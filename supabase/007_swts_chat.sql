-- Sepid Island SWTS experiment conversations and research logging.
-- Run once after migrations 001-006.

create table if not exists public.swts_runs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.participant_sessions(id) on delete cascade,
  swts_version text not null,
  task_order text[] not null,
  current_position integer not null default 0 check (current_position between 0 and 3),
  status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'abandoned')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  check (
    cardinality(task_order) = 3
    and task_order <@ array['task_1', 'task_2', 'task_3']::text[]
    and task_order @> array['task_1', 'task_2', 'task_3']::text[]
  )
);

create table if not exists public.swts_task_sessions (
  id uuid primary key,
  run_id uuid not null references public.swts_runs(id) on delete cascade,
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  task_id text not null check (task_id in ('task_1', 'task_2', 'task_3')),
  task_position integer not null check (task_position between 0 and 2),
  rag_session_id text not null unique check (length(rag_session_id) between 1 and 200),
  task_version text not null,
  status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'abandoned')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  final_response text,
  effort smallint check (effort between 1 and 5),
  confidence smallint check (confidence between 1 and 5),
  client_submitted_at timestamptz,
  unique (run_id, task_id),
  unique (run_id, task_position)
);

create table if not exists public.swts_chat_attempts (
  id uuid primary key,
  task_session_id uuid not null references public.swts_task_sessions(id) on delete cascade,
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  task_id text not null check (task_id in ('task_1', 'task_2', 'task_3')),
  rag_session_id text not null,
  sequence_number integer not null check (sequence_number >= 1),
  participant_message text not null check (length(participant_message) between 1 and 8000),
  client_sent_at timestamptz not null,
  server_attempt_started_at timestamptz not null default now(),
  response_received_at timestamptz,
  latency_ms numeric(14,2),
  success boolean,
  status text not null default 'pending' check (status in ('pending', 'success', 'failure')),
  request_id text,
  original_backend_answer text,
  participant_visible_answer text,
  sources jsonb not null default '[]'::jsonb,
  retrieval jsonb not null default '{}'::jsonb,
  prompt_version text,
  error_category text,
  manual_retry boolean not null default false,
  retry_of uuid references public.swts_chat_attempts(id),
  server_finished_at timestamptz,
  unique (task_session_id, sequence_number)
);

create index if not exists swts_task_sessions_session_idx
  on public.swts_task_sessions(session_id, task_position);
create index if not exists swts_chat_attempts_session_idx
  on public.swts_chat_attempts(session_id, task_id, sequence_number);

alter table public.swts_runs enable row level security;
alter table public.swts_task_sessions enable row level security;
alter table public.swts_chat_attempts enable row level security;

revoke all on public.swts_runs, public.swts_task_sessions, public.swts_chat_attempts
  from anon, authenticated;

create or replace function public.start_or_restore_swts(
  p_session_id uuid,
  p_recovery_token text
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  participant_row public.participant_sessions%rowtype;
  run_row public.swts_runs%rowtype;
  task_row public.swts_task_sessions%rowtype;
  selected_order text[];
  task_session_id uuid;
  task_name text;
  exchanges jsonb;
  next_sequence integer;
  order_number integer;
begin
  -- Completed participants may reopen the page to see the completion state,
  -- but no write RPC below accepts a completed participant session.
  if not exists (
    select 1 from public.participant_sessions s
    where s.id = p_session_id
      and s.recovery_token_hash = encode(digest(p_recovery_token, 'sha256'), 'hex')
      and (s.completed_at is null or exists (
        select 1 from public.swts_runs r
        where r.session_id = s.id and r.status = 'completed'
      ))
  ) then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_session');
  end if;

  select * into participant_row
  from public.participant_sessions
  where id = p_session_id;

  select * into run_row
  from public.swts_runs
  where session_id = p_session_id
  for update;

  if not found then
    order_number := mod(abs(hashtextextended(p_session_id::text, 0)), 6)::integer;
    selected_order := case order_number
      when 0 then array['task_1', 'task_2', 'task_3']
      when 1 then array['task_1', 'task_3', 'task_2']
      when 2 then array['task_2', 'task_1', 'task_3']
      when 3 then array['task_2', 'task_3', 'task_1']
      when 4 then array['task_3', 'task_1', 'task_2']
      else array['task_3', 'task_2', 'task_1']
    end;

    insert into public.swts_runs (session_id, swts_version, task_order)
    values (p_session_id, 'sepid-island-fa-swts-v1', selected_order)
    returning * into run_row;
  end if;

  update public.participant_sessions
  set current_phase = 'chat', last_seen_at = now()
  where id = p_session_id;

  if run_row.status = 'completed' then
    return jsonb_build_object(
      'accepted', true,
      'status', 'completed',
      'run_id', run_row.id,
      'current_position', 3,
      'total_tasks', 3,
      'task_order', to_jsonb(run_row.task_order),
      'task_id', null,
      'rag_session_id', null,
      'task_started_at', null,
      'exchanges', '[]'::jsonb,
      'next_sequence', 1
    );
  end if;

  task_name := run_row.task_order[run_row.current_position + 1];
  select * into task_row
  from public.swts_task_sessions
  where run_id = run_row.id and task_position = run_row.current_position;

  if not found then
    task_session_id := gen_random_uuid();
    insert into public.swts_task_sessions (
      id, run_id, session_id, task_id, task_position, rag_session_id, task_version
    ) values (
      task_session_id,
      run_row.id,
      p_session_id,
      task_name,
      run_row.current_position,
      participant_row.participant_id::text || '-' || task_name || '-' || left(task_session_id::text, 8),
      'sepid-island-fa-swts-v1'
    ) returning * into task_row;
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'attempt_id', a.id,
    'sequence_number', a.sequence_number,
    'participant_message', a.participant_message,
    'participant_visible_answer', a.participant_visible_answer,
    'success', a.success,
    'error_category', a.error_category,
    'manual_retry', a.manual_retry,
    'client_sent_at', a.client_sent_at,
    'response_received_at', a.response_received_at
  ) order by a.sequence_number), '[]'::jsonb)
  into exchanges
  from public.swts_chat_attempts a
  where a.task_session_id = task_row.id;

  select coalesce(max(a.sequence_number), 0) + 1
  into next_sequence
  from public.swts_chat_attempts a
  where a.task_session_id = task_row.id;

  return jsonb_build_object(
    'accepted', true,
    'status', 'in_progress',
    'run_id', run_row.id,
    'current_position', run_row.current_position,
    'total_tasks', 3,
    'task_order', to_jsonb(run_row.task_order),
    'task_id', task_row.task_id,
    'rag_session_id', task_row.rag_session_id,
    'task_started_at', task_row.started_at,
    'exchanges', exchanges,
    'next_sequence', next_sequence
  );
end;
$$;

create or replace function public.begin_swts_attempt(
  p_session_id uuid,
  p_recovery_token text,
  p_attempt_id uuid,
  p_task_id text,
  p_sequence_number integer,
  p_participant_message text,
  p_client_sent_at timestamptz,
  p_manual_retry boolean default false,
  p_retry_of uuid default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  task_row public.swts_task_sessions%rowtype;
begin
  if not public.session_is_valid(p_session_id, p_recovery_token) then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_session');
  end if;
  if p_task_id not in ('task_1', 'task_2', 'task_3') then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_task');
  end if;
  if nullif(trim(p_participant_message), '') is null or length(p_participant_message) > 8000 then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_message');
  end if;

  select ts.* into task_row
  from public.swts_task_sessions ts
  join public.swts_runs r on r.id = ts.run_id
  where ts.session_id = p_session_id
    and ts.task_id = p_task_id
    and ts.task_position = r.current_position
    and ts.status = 'in_progress'
    and r.status = 'in_progress'
  for update of ts;

  if not found then
    return jsonb_build_object('accepted', false, 'reason', 'task_not_active');
  end if;

  insert into public.swts_chat_attempts (
    id, task_session_id, session_id, task_id, rag_session_id,
    sequence_number, participant_message, client_sent_at,
    manual_retry, retry_of
  ) values (
    p_attempt_id, task_row.id, p_session_id, p_task_id, task_row.rag_session_id,
    p_sequence_number, p_participant_message, p_client_sent_at,
    coalesce(p_manual_retry, false), p_retry_of
  ) on conflict (id) do nothing;

  update public.participant_sessions set last_seen_at = now() where id = p_session_id;
  return jsonb_build_object('accepted', true, 'attempt_id', p_attempt_id);
exception
  when unique_violation then
    return jsonb_build_object('accepted', false, 'reason', 'duplicate_sequence');
end;
$$;

create or replace function public.finish_swts_attempt(
  p_session_id uuid,
  p_recovery_token text,
  p_attempt_id uuid,
  p_success boolean,
  p_response_received_at timestamptz,
  p_latency_ms numeric,
  p_request_id text default null,
  p_original_backend_answer text default null,
  p_participant_visible_answer text default null,
  p_sources jsonb default '[]'::jsonb,
  p_retrieval jsonb default '{}'::jsonb,
  p_prompt_version text default null,
  p_error_category text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  updated_id uuid;
begin
  if not public.session_is_valid(p_session_id, p_recovery_token) then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_session');
  end if;

  update public.swts_chat_attempts
  set response_received_at = p_response_received_at,
      latency_ms = p_latency_ms,
      success = p_success,
      status = case when p_success then 'success' else 'failure' end,
      request_id = p_request_id,
      original_backend_answer = p_original_backend_answer,
      participant_visible_answer = p_participant_visible_answer,
      sources = coalesce(p_sources, '[]'::jsonb),
      retrieval = coalesce(p_retrieval, '{}'::jsonb),
      prompt_version = p_prompt_version,
      error_category = case when p_success then null else coalesce(p_error_category, 'unknown') end,
      server_finished_at = now()
  where id = p_attempt_id
    and session_id = p_session_id
    and status = 'pending'
  returning id into updated_id;

  if updated_id is null then
    if exists (select 1 from public.swts_chat_attempts where id = p_attempt_id and session_id = p_session_id and status <> 'pending') then
      return jsonb_build_object('accepted', true, 'attempt_id', p_attempt_id, 'already_finished', true);
    end if;
    return jsonb_build_object('accepted', false, 'reason', 'attempt_not_found');
  end if;

  update public.participant_sessions set last_seen_at = now() where id = p_session_id;
  return jsonb_build_object('accepted', true, 'attempt_id', updated_id);
end;
$$;

create or replace function public.submit_swts_task(
  p_session_id uuid,
  p_recovery_token text,
  p_task_id text,
  p_final_response text,
  p_effort integer,
  p_confidence integer,
  p_client_submitted_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  run_row public.swts_runs%rowtype;
  task_row public.swts_task_sessions%rowtype;
  next_task text;
  next_task_session_id uuid;
  participant_identifier uuid;
begin
  if not public.session_is_valid(p_session_id, p_recovery_token) then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_session');
  end if;
  if nullif(trim(p_final_response), '') is null then
    return jsonb_build_object('accepted', false, 'reason', 'final_response_required');
  end if;
  if p_task_id = 'task_3'
     and cardinality(regexp_split_to_array(trim(p_final_response), E'\\s+')) > 300 then
    return jsonb_build_object('accepted', false, 'reason', 'final_response_too_long');
  end if;
  if p_effort is null or p_effort not between 1 and 5
     or p_confidence is null or p_confidence not between 1 and 5 then
    return jsonb_build_object('accepted', false, 'reason', 'feedback_out_of_range');
  end if;

  select * into run_row from public.swts_runs where session_id = p_session_id for update;
  if not found or run_row.status <> 'in_progress' then
    return jsonb_build_object('accepted', false, 'reason', 'run_not_active');
  end if;

  select * into task_row
  from public.swts_task_sessions
  where run_id = run_row.id and task_position = run_row.current_position
  for update;

  if not found or task_row.task_id <> p_task_id or task_row.status <> 'in_progress' then
    return jsonb_build_object('accepted', false, 'reason', 'task_not_active');
  end if;
  if exists (select 1 from public.swts_chat_attempts where task_session_id = task_row.id and status = 'pending') then
    return jsonb_build_object('accepted', false, 'reason', 'pending_chat_log');
  end if;

  update public.swts_task_sessions
  set status = 'completed', completed_at = now(),
      final_response = p_final_response, effort = p_effort,
      confidence = p_confidence, client_submitted_at = p_client_submitted_at
  where id = task_row.id;

  if run_row.current_position >= 2 then
    update public.swts_runs set status = 'completed', current_position = 3, completed_at = now() where id = run_row.id;
    update public.invitations i set status = 'completed'
    from public.participant_sessions s
    where s.id = p_session_id and i.id = s.invitation_id;
    update public.participant_sessions set last_seen_at = now(), completed_at = now() where id = p_session_id;
    return jsonb_build_object('accepted', true, 'completed', true);
  end if;

  update public.swts_runs
  set current_position = current_position + 1
  where id = run_row.id
  returning * into run_row;

  next_task := run_row.task_order[run_row.current_position + 1];
  next_task_session_id := gen_random_uuid();
  select participant_id into participant_identifier from public.participant_sessions where id = p_session_id;

  insert into public.swts_task_sessions (
    id, run_id, session_id, task_id, task_position, rag_session_id, task_version
  ) values (
    next_task_session_id, run_row.id, p_session_id, next_task, run_row.current_position,
    participant_identifier::text || '-' || next_task || '-' || left(next_task_session_id::text, 8),
    run_row.swts_version
  ) on conflict (run_id, task_position) do nothing;

  update public.participant_sessions set last_seen_at = now() where id = p_session_id;
  return jsonb_build_object('accepted', true, 'completed', false, 'next_task_id', next_task);
end;
$$;

revoke all on function public.start_or_restore_swts(uuid, text) from public;
revoke all on function public.begin_swts_attempt(uuid, text, uuid, text, integer, text, timestamptz, boolean, uuid) from public;
revoke all on function public.finish_swts_attempt(uuid, text, uuid, boolean, timestamptz, numeric, text, text, text, jsonb, jsonb, text, text) from public;
revoke all on function public.submit_swts_task(uuid, text, text, text, integer, integer, timestamptz) from public;

grant execute on function public.start_or_restore_swts(uuid, text) to anon, authenticated;
grant execute on function public.begin_swts_attempt(uuid, text, uuid, text, integer, text, timestamptz, boolean, uuid) to anon, authenticated;
grant execute on function public.finish_swts_attempt(uuid, text, uuid, boolean, timestamptz, numeric, text, text, text, jsonb, jsonb, text, text) to anon, authenticated;
grant execute on function public.submit_swts_task(uuid, text, text, text, integer, integer, timestamptz) to anon, authenticated;

create or replace function public.researcher_swts_details(p_session_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;

  select jsonb_build_object(
    'run', (select to_jsonb(r) from public.swts_runs r where r.session_id = p_session_id),
    'tasks', coalesce((select jsonb_agg(to_jsonb(ts) order by ts.task_position) from public.swts_task_sessions ts where ts.session_id = p_session_id), '[]'::jsonb),
    'attempts', coalesce((select jsonb_agg(to_jsonb(a) order by ts.task_position, a.sequence_number)
      from public.swts_chat_attempts a
      join public.swts_task_sessions ts on ts.id = a.task_session_id
      where a.session_id = p_session_id), '[]'::jsonb)
  ) into result;
  return result;
end;
$$;

create or replace function public.researcher_export_swts()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.participant_id, x.task_position, x.sequence_number), '[]'::jsonb)
  into result
  from (
    select
      s.participant_id,
      r.swts_version,
      ts.task_id,
      ts.task_position,
      ts.rag_session_id,
      ts.status as task_status,
      ts.started_at as task_started_at,
      ts.completed_at as task_completed_at,
      ts.final_response,
      ts.effort,
      ts.confidence,
      a.id as attempt_id,
      a.sequence_number,
      a.participant_message,
      a.client_sent_at,
      a.response_received_at,
      a.latency_ms,
      a.status as attempt_status,
      a.request_id,
      a.original_backend_answer,
      a.participant_visible_answer,
      a.sources,
      a.retrieval,
      a.prompt_version,
      a.error_category,
      a.manual_retry,
      a.retry_of
    from public.swts_task_sessions ts
    join public.swts_runs r on r.id = ts.run_id
    join public.participant_sessions s on s.id = ts.session_id
    left join public.swts_chat_attempts a on a.task_session_id = ts.id
  ) x;
  return result;
end;
$$;

revoke all on function public.researcher_swts_details(uuid) from public;
revoke all on function public.researcher_export_swts() from public;
grant execute on function public.researcher_swts_details(uuid) to authenticated;
grant execute on function public.researcher_export_swts() to authenticated;
