create table if not exists public.test_trial_responses (
  id uuid primary key,
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  test_version text not null,
  trial_id text not null,
  trial_index integer not null,
  trial_kind text not null,
  response_value text not null,
  reaction_time_ms numeric(12,2) not null check (reaction_time_ms >= 0),
  page_hidden boolean not null default false,
  input_method text,
  client_created_at timestamptz not null,
  server_received_at timestamptz not null default now(),
  unique (session_id, test_version, trial_id)
);

alter table public.test_trial_responses enable row level security;
revoke all on public.test_trial_responses from anon, authenticated;

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
    ) on conflict (id) do nothing;
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

create or replace function public.create_study_invitation(p_code text, p_expires_at timestamptz default null)
returns table (invitation_id uuid, invitation_status text, created_at timestamptz)
language plpgsql
security definer
set search_path = public, extensions
as $$
begin
  if nullif(trim(p_code), '') is null then
    raise exception 'Invitation code cannot be empty';
  end if;

  return query
  insert into public.invitations (experiment_id, code_hash, expires_at)
  select e.id, encode(digest(upper(trim(p_code)), 'sha256'), 'hex'), p_expires_at
  from public.experiments e
  where e.name = 'Cognitive Style Research' and e.version = '0.1'
  returning invitations.id, invitations.status, invitations.created_at;
end;
$$;

revoke all on function public.create_study_invitation(text, timestamptz) from public;
