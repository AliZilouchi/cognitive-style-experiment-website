-- Conversation-centred SWTS v2. Existing runs keep their original version;
-- newly created runs and task sessions are labelled v2.

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
    values (p_session_id, 'sepid-island-fa-swts-v2', selected_order)
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
      run_row.swts_version
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

revoke all on function public.start_or_restore_swts(uuid, text) from public;
grant execute on function public.start_or_restore_swts(uuid, text) to anon, authenticated;
