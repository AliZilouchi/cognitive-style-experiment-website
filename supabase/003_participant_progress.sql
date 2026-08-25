create table if not exists public.consents (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  consent_version text not null,
  accepted boolean not null,
  accepted_at timestamptz not null default now(),
  unique (session_id, consent_version)
);

create table if not exists public.demographic_responses (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  form_version text not null,
  responses jsonb not null default '{}'::jsonb,
  submitted_at timestamptz not null default now(),
  unique (session_id, form_version)
);

create table if not exists public.participant_events (
  id uuid primary key,
  session_id uuid not null references public.participant_sessions(id) on delete cascade,
  sequence_number bigint not null,
  event_type text not null,
  event_payload jsonb not null default '{}'::jsonb,
  client_created_at timestamptz not null,
  server_received_at timestamptz not null default now(),
  unique (session_id, sequence_number)
);

alter table public.consents enable row level security;
alter table public.demographic_responses enable row level security;
alter table public.participant_events enable row level security;

revoke all on public.consents, public.demographic_responses, public.participant_events from anon, authenticated;

create or replace function public.session_is_valid(p_session_id uuid, p_recovery_token text)
returns boolean
language sql
stable
security definer
set search_path = public, extensions
as $$
  select exists (
    select 1 from public.participant_sessions s
    where s.id = p_session_id
      and s.recovery_token_hash = encode(digest(p_recovery_token, 'sha256'), 'hex')
      and s.completed_at is null
  );
$$;

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

create or replace function public.restore_participant_session(
  p_session_id uuid,
  p_recovery_token text
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  session_row public.participant_sessions%rowtype;
begin
  if not public.session_is_valid(p_session_id, p_recovery_token) then
    return jsonb_build_object('accepted', false);
  end if;

  select * into session_row from public.participant_sessions where id = p_session_id;
  update public.participant_sessions set last_seen_at = now() where id = p_session_id;

  return jsonb_build_object(
    'accepted', true,
    'session_id', session_row.id,
    'participant_id', session_row.participant_id,
    'phase', session_row.current_phase
  );
end;
$$;

revoke all on function public.session_is_valid(uuid, text) from public;
revoke all on function public.save_participant_event(uuid, text, uuid, bigint, text, jsonb, timestamptz) from public;
revoke all on function public.restore_participant_session(uuid, text) from public;
grant execute on function public.save_participant_event(uuid, text, uuid, bigint, text, jsonb, timestamptz) to anon, authenticated;
grant execute on function public.restore_participant_session(uuid, text) to anon, authenticated;
