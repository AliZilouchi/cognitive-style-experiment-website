-- Complete researcher export for every non-archived participant session.
-- Run once after migrations 001-012.

create or replace function public.researcher_export_complete_dataset()
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

  with eligible_sessions as materialized (
    select s.id
    from public.participant_sessions s
    where s.archived_at is null
  )
  select jsonb_build_object(
    'schema_version', 'cognitive-style-complete-export-v1',
    'exported_at', now(),
    'filter', 'participant_sessions.archived_at IS NULL',
    'session_count', (select count(*) from eligible_sessions),
    'participant_sessions', coalesce((
      select jsonb_agg(
        (to_jsonb(s) - 'recovery_token_hash') || jsonb_build_object(
          'invitation_code', i.plaintext_code,
          'invitation_status', i.status,
          'invitation_expires_at', i.expires_at
        ) order by s.created_at
      )
      from public.participant_sessions s
      join eligible_sessions e on e.id = s.id
      join public.invitations i on i.id = s.invitation_id
    ), '[]'::jsonb),
    'consents', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.accepted_at)
      from public.consents x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'demographic_responses', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.submitted_at)
      from public.demographic_responses x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'participant_events', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.session_id, x.sequence_number)
      from public.participant_events x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'participant_test_runs', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.started_at)
      from public.participant_test_runs x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'test_trial_responses', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.session_id, x.trial_index)
      from public.test_trial_responses x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'study_form_responses', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.session_id, x.submitted_at)
      from public.study_form_responses x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'swts_runs', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.started_at)
      from public.swts_runs x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'swts_task_sessions', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.session_id, x.task_position)
      from public.swts_task_sessions x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb),
    'swts_chat_attempts', coalesce((
      select jsonb_agg(to_jsonb(x) order by x.session_id, x.task_id, x.sequence_number)
      from public.swts_chat_attempts x join eligible_sessions e on e.id = x.session_id
    ), '[]'::jsonb)
  ) into result;

  return result;
end;
$$;

revoke all on function public.researcher_export_complete_dataset() from public;
grant execute on function public.researcher_export_complete_dataset() to authenticated;

-- Keep the existing individual exports consistent with the complete export.
create or replace function public.researcher_export_trials()
returns jsonb language plpgsql security definer set search_path = public as $$
declare result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(to_jsonb(t) order by t.participant_id, t.trial_index), '[]'::jsonb)
  into result from (
    select s.participant_id, tr.test_version, tr.trial_id, tr.trial_index,
      tr.trial_kind, tr.subtest, tr.response_value, tr.correct_answer,
      tr.is_correct, tr.reaction_time_ms, tr.page_hidden, tr.focus_lost_count,
      tr.input_method, tr.client_created_at, tr.server_received_at
    from public.test_trial_responses tr
    join public.participant_sessions s on s.id = tr.session_id
    where s.archived_at is null
  ) t;
  return result;
end;
$$;

create or replace function public.researcher_export_study_forms()
returns jsonb language plpgsql security definer set search_path = public as $$
declare result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(to_jsonb(f) order by f.participant_id, f.submitted_at), '[]'::jsonb)
  into result from (
    select s.participant_id, r.form_name, r.form_version, r.task_id,
      r.task_position, r.responses, r.submitted_at
    from public.study_form_responses r
    join public.participant_sessions s on s.id = r.session_id
    where s.archived_at is null
  ) f;
  return result;
end;
$$;

create or replace function public.researcher_export_swts()
returns jsonb language plpgsql security definer set search_path = public as $$
declare result jsonb;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;
  select coalesce(jsonb_agg(to_jsonb(x) order by x.participant_id, x.task_position, x.sequence_number), '[]'::jsonb)
  into result from (
    select s.participant_id, r.swts_version, ts.task_id, ts.task_position,
      ts.rag_session_id, ts.status as task_status, ts.started_at as task_started_at,
      ts.completed_at as task_completed_at, ts.final_response, ts.effort,
      ts.confidence, a.id as attempt_id, a.sequence_number,
      a.participant_message, a.client_sent_at, a.response_received_at,
      a.latency_ms, a.status as attempt_status, a.request_id,
      a.original_backend_answer, a.participant_visible_answer, a.sources,
      a.retrieval, a.prompt_version, a.error_category, a.manual_retry, a.retry_of
    from public.swts_task_sessions ts
    join public.swts_runs r on r.id = ts.run_id
    join public.participant_sessions s on s.id = ts.session_id
    left join public.swts_chat_attempts a on a.task_session_id = ts.id
    where s.archived_at is null
  ) x;
  return result;
end;
$$;

revoke all on function public.researcher_export_trials() from public;
revoke all on function public.researcher_export_study_forms() from public;
revoke all on function public.researcher_export_swts() from public;
grant execute on function public.researcher_export_trials() to authenticated;
grant execute on function public.researcher_export_study_forms() to authenticated;
grant execute on function public.researcher_export_swts() to authenticated;
