-- Persian-first study flow, task questionnaires, delayed completion, and
-- protected researcher form exports. Run once after migrations 001-007.

create table if not exists public.study_form_responses (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  form_name text not null check (form_name in ('demographics', 'think_aloud', 'pre_task', 'post_task', 'final_comparative')),
  form_version text not null,
  task_id text not null default '',
  task_position integer,
  responses jsonb not null default '{}'::jsonb,
  submitted_at timestamptz not null default now(),
  unique (session_id, form_name, task_id, form_version)
);

alter table public.study_form_responses enable row level security;
revoke all on public.study_form_responses from anon, authenticated;

update public.participant_sessions
set current_phase = 'swts'
where current_phase = 'chat' and completed_at is null;

create or replace function public.capture_persian_study_flow_event()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  form_key text;
  task_key text := coalesce(new.event_payload->>'task_id', '');
  response_payload jsonb;
  requested_phase text := new.event_payload->>'phase';
begin
  form_key := case new.event_type
    when 'demographics_submitted' then 'demographics'
    when 'think_aloud_acknowledged' then 'think_aloud'
    when 'swts_pre_task_submitted' then 'pre_task'
    when 'swts_post_task_submitted' then 'post_task'
    when 'final_comparative_submitted' then 'final_comparative'
    else null
  end;

  if form_key is not null then
    response_payload := case
      when new.event_payload ? 'responses' then new.event_payload->'responses'
      else new.event_payload - 'phase' - 'version' - 'task_id' - 'task_position'
    end;

    insert into public.study_form_responses
      (session_id, form_name, form_version, task_id, task_position, responses, submitted_at)
    values
      (new.session_id, form_key, coalesce(new.event_payload->>'version', 'fa-v1'), task_key,
       nullif(new.event_payload->>'task_position', '')::integer,
       coalesce(response_payload, '{}'::jsonb), now())
    on conflict (session_id, form_name, task_id, form_version)
    do update set responses = excluded.responses,
                  task_position = excluded.task_position,
                  submitted_at = now();
  end if;

  if requested_phase in ('introduction', 'demographics', 'test', 'think_aloud', 'pre_task', 'swts', 'post_task', 'comparative', 'complete') then
    update public.participant_sessions
    set current_phase = requested_phase, last_seen_at = now()
    where id = new.session_id;
  end if;

  if new.event_type = 'final_comparative_submitted' then
    update public.participant_sessions
    set current_phase = 'complete', last_seen_at = now(), completed_at = coalesce(completed_at, now())
    where id = new.session_id;

    update public.invitations i
    set status = 'completed'
    from public.participant_sessions s
    where s.id = new.session_id and i.id = s.invitation_id;
  end if;

  return new;
end;
$$;

drop trigger if exists participant_events_persian_flow on public.participant_events;
create trigger participant_events_persian_flow
after insert on public.participant_events
for each row execute function public.capture_persian_study_flow_event();

-- Task submission deliberately completes only the SWTS run. The participant
-- session and invitation remain active for the post-task and final-comparison
-- forms, and are completed by the trigger above.
create or replace function public.submit_swts_task_v2(
  p_session_id uuid,
  p_recovery_token text,
  p_task_id text,
  p_final_response text,
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
  if p_task_id not in ('task_1', 'task_2', 'task_3') then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_task');
  end if;
  if nullif(trim(p_final_response), '') is null then
    return jsonb_build_object('accepted', false, 'reason', 'final_response_required');
  end if;
  if p_task_id = 'task_3' and cardinality(regexp_split_to_array(trim(p_final_response), E'\\s+')) > 300 then
    return jsonb_build_object('accepted', false, 'reason', 'final_response_too_long');
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
  set status = 'completed', completed_at = now(), final_response = trim(p_final_response),
      client_submitted_at = p_client_submitted_at
  where id = task_row.id;

  if run_row.current_position >= 2 then
    update public.swts_runs set status = 'completed', current_position = 3, completed_at = now() where id = run_row.id;
    update public.participant_sessions set current_phase = 'post_task', last_seen_at = now() where id = p_session_id;
    return jsonb_build_object('accepted', true, 'completed', true);
  end if;

  update public.swts_runs set current_position = current_position + 1 where id = run_row.id returning * into run_row;
  next_task := run_row.task_order[run_row.current_position + 1];
  next_task_session_id := gen_random_uuid();
  select participant_id into participant_identifier from public.participant_sessions where id = p_session_id;

  insert into public.swts_task_sessions
    (id, run_id, session_id, task_id, task_position, rag_session_id, task_version)
  values
    (next_task_session_id, run_row.id, p_session_id, next_task, run_row.current_position,
     participant_identifier::text || '-' || next_task || '-' || left(next_task_session_id::text, 8), run_row.swts_version)
  on conflict (run_id, task_position) do nothing;

  update public.participant_sessions set current_phase = 'post_task', last_seen_at = now() where id = p_session_id;
  return jsonb_build_object('accepted', true, 'completed', false, 'next_task_id', next_task);
end;
$$;

revoke all on function public.submit_swts_task_v2(uuid, text, text, text, timestamptz) from public;
grant execute on function public.submit_swts_task_v2(uuid, text, text, text, timestamptz) to anon, authenticated;

create or replace function public.researcher_study_form_details(p_session_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(to_jsonb(f) order by f.submitted_at), '[]'::jsonb)
  into result
  from (
    select form_name, form_version, task_id, task_position, responses, submitted_at
    from public.study_form_responses where session_id = p_session_id
  ) f;
  return result;
end;
$$;

create or replace function public.researcher_export_study_forms()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(to_jsonb(f) order by f.participant_id, f.submitted_at), '[]'::jsonb)
  into result
  from (
    select s.participant_id, r.form_name, r.form_version, r.task_id, r.task_position,
           r.responses, r.submitted_at
    from public.study_form_responses r
    join public.participant_sessions s on s.id = r.session_id
  ) f;
  return result;
end;
$$;

revoke all on function public.researcher_study_form_details(uuid) from public;
revoke all on function public.researcher_export_study_forms() from public;
grant execute on function public.researcher_study_form_details(uuid) to authenticated;
grant execute on function public.researcher_export_study_forms() to authenticated;
