create table if not exists public.participant_test_runs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  test_version text not null,
  scoring_version text not null,
  status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'abandoned')),
  current_index integer not null default 0,
  trial_order jsonb not null default '[]'::jsonb,
  analytic_median_ms numeric(12,2),
  wholistic_median_ms numeric(12,2),
  wholistic_analytic_ratio numeric(12,6),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (session_id, test_version)
);

alter table public.participant_test_runs enable row level security;
revoke all on public.participant_test_runs from anon, authenticated;

alter table public.test_trial_responses add column if not exists subtest text;
alter table public.test_trial_responses add column if not exists is_practice boolean not null default false;
alter table public.test_trial_responses add column if not exists is_correct boolean;
alter table public.test_trial_responses add column if not exists correct_answer text;
alter table public.test_trial_responses add column if not exists timed_out boolean not null default false;
alter table public.test_trial_responses add column if not exists focus_lost_count integer not null default 0;
alter table public.test_trial_responses add column if not exists viewport jsonb not null default '{}'::jsonb;

create or replace function public.save_participant_event(
  p_session_id uuid,
  p_recovery_token text,
  p_event_id uuid,
  p_sequence_number bigint,
  p_event_type text,
  p_event_payload jsonb,
  p_client_created_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  requested_phase text;
begin
  if not public.session_is_valid(p_session_id, p_recovery_token) then
    return jsonb_build_object('accepted', false, 'reason', 'invalid_session');
  end if;

  insert into public.participant_events
    (id, session_id, sequence_number, event_type, event_payload, client_created_at)
  values
    (p_event_id, p_session_id, p_sequence_number, p_event_type,
     coalesce(p_event_payload, '{}'::jsonb), p_client_created_at)
  on conflict (id) do nothing;

  if p_event_type = 'consent_submitted' then
    insert into public.consents (session_id, consent_version, accepted)
    values (p_session_id, coalesce(p_event_payload->>'version', '0.1'),
            coalesce((p_event_payload->>'accepted')::boolean, false))
    on conflict (session_id, consent_version)
    do update set accepted = excluded.accepted, accepted_at = now();

  elsif p_event_type = 'demographics_submitted' then
    insert into public.demographic_responses (session_id, form_version, responses)
    values (p_session_id, coalesce(p_event_payload->>'version', '0.1'),
            coalesce(p_event_payload->'responses', '{}'::jsonb))
    on conflict (session_id, form_version)
    do update set responses = excluded.responses, submitted_at = now();

  elsif p_event_type = 'timing_check_completed' then
    insert into public.test_trial_responses (
      id, session_id, test_version, trial_id, trial_index, trial_kind,
      response_value, reaction_time_ms, page_hidden, input_method, client_created_at
    ) values (
      p_event_id, p_session_id,
      coalesce(p_event_payload->>'version', 'engine-check-0.1'),
      coalesce(p_event_payload->>'trial_id', 'timing-check-01'),
      coalesce((p_event_payload->>'trial_index')::integer, 0),
      'timing_check', coalesce(p_event_payload->>'response', 'unknown'),
      coalesce((p_event_payload->>'reaction_time_ms')::numeric, 0),
      coalesce((p_event_payload->>'page_hidden')::boolean, false),
      p_event_payload->>'input_method', p_client_created_at
    ) on conflict (session_id, test_version, trial_id) do nothing;

  elsif p_event_type = 'ecsa_test_started' then
    insert into public.participant_test_runs
      (session_id, test_version, scoring_version, trial_order)
    values
      (p_session_id, p_event_payload->>'test_version', p_event_payload->>'scoring_version',
       coalesce(p_event_payload->'trial_order', '[]'::jsonb))
    on conflict (session_id, test_version) do nothing;

  elsif p_event_type = 'ecsa_trial_completed' then
    insert into public.test_trial_responses (
      id, session_id, test_version, trial_id, trial_index, trial_kind,
      response_value, reaction_time_ms, page_hidden, input_method, client_created_at,
      subtest, is_practice, is_correct, correct_answer, timed_out, focus_lost_count, viewport
    ) values (
      p_event_id, p_session_id, p_event_payload->>'test_version',
      p_event_payload->>'trial_id', (p_event_payload->>'trial_index')::integer,
      case when coalesce((p_event_payload->>'is_practice')::boolean, false) then 'practice' else 'research' end,
      p_event_payload->>'response', (p_event_payload->>'reaction_time_ms')::numeric,
      coalesce((p_event_payload->>'page_hidden')::boolean, false), p_event_payload->>'input_method',
      p_client_created_at, p_event_payload->>'subtest',
      coalesce((p_event_payload->>'is_practice')::boolean, false),
      (p_event_payload->>'is_correct')::boolean, p_event_payload->>'correct_answer',
      coalesce((p_event_payload->>'timed_out')::boolean, false),
      coalesce((p_event_payload->>'focus_lost_count')::integer, 0),
      coalesce(p_event_payload->'viewport', '{}'::jsonb)
    ) on conflict (session_id, test_version, trial_id) do nothing;

    update public.participant_test_runs
    set current_index = greatest(current_index, (p_event_payload->>'trial_index')::integer + 1)
    where session_id = p_session_id and test_version = p_event_payload->>'test_version';

  elsif p_event_type = 'ecsa_test_completed' then
    update public.participant_test_runs
    set status = 'completed',
        analytic_median_ms = (p_event_payload->>'analytic_median_ms')::numeric,
        wholistic_median_ms = (p_event_payload->>'wholistic_median_ms')::numeric,
        wholistic_analytic_ratio = (p_event_payload->>'wholistic_analytic_ratio')::numeric,
        completed_at = now(), current_index = 84
    where session_id = p_session_id and test_version = p_event_payload->>'test_version';
  end if;

  requested_phase := p_event_payload->>'phase';
  if requested_phase in ('introduction', 'demographics', 'test', 'chat') then
    update public.participant_sessions
    set current_phase = requested_phase, last_seen_at = now()
    where id = p_session_id;
  else
    update public.participant_sessions set last_seen_at = now() where id = p_session_id;
  end if;

  return jsonb_build_object('accepted', true, 'event_id', p_event_id);
end;
$$;

revoke all on function public.save_participant_event(uuid, text, uuid, bigint, text, jsonb, timestamptz) from public;
grant execute on function public.save_participant_event(uuid, text, uuid, bigint, text, jsonb, timestamptz) to anon, authenticated;
