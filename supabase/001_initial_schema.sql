create extension if not exists pgcrypto;

create table if not exists public.experiments (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  version text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (name, version)
);

create table if not exists public.invitations (
  id uuid primary key default gen_random_uuid(),
  experiment_id uuid not null references public.experiments(id),
  code_hash text not null unique,
  status text not null default 'unused' check (status in ('unused', 'started', 'completed', 'revoked')),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  started_at timestamptz
);

create table if not exists public.participant_sessions (
  id uuid primary key default gen_random_uuid(),
  invitation_id uuid not null unique references public.invitations(id),
  participant_id uuid not null default gen_random_uuid(),
  recovery_token_hash text not null,
  current_phase text not null default 'introduction',
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  completed_at timestamptz
);

alter table public.experiments enable row level security;
alter table public.invitations enable row level security;
alter table public.participant_sessions enable row level security;

revoke all on public.experiments, public.invitations, public.participant_sessions from anon, authenticated;

create or replace function public.redeem_invitation(invitation_code text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  matched_invitation public.invitations%rowtype;
  new_session public.participant_sessions%rowtype;
  recovery_token text := encode(gen_random_bytes(24), 'hex');
begin
  select * into matched_invitation
  from public.invitations
  where code_hash = encode(digest(upper(trim(invitation_code)), 'sha256'), 'hex')
    and status = 'unused'
    and (expires_at is null or expires_at > now())
  for update;

  if not found then
    return jsonb_build_object('accepted', false);
  end if;

  update public.invitations
  set status = 'started', started_at = now()
  where id = matched_invitation.id;

  insert into public.participant_sessions (invitation_id, recovery_token_hash)
  values (matched_invitation.id, encode(digest(recovery_token, 'sha256'), 'hex'))
  returning * into new_session;

  return jsonb_build_object(
    'accepted', true,
    'session_id', new_session.id,
    'participant_id', new_session.participant_id,
    'recovery_token', recovery_token,
    'phase', new_session.current_phase
  );
end;
$$;

revoke all on function public.redeem_invitation(text) from public;
grant execute on function public.redeem_invitation(text) to anon, authenticated;

insert into public.experiments (name, version)
values ('Cognitive Style Research', '0.1')
on conflict (name, version) do nothing;

-- Create an invitation by replacing FIRST-TEST-CODE before running this statement.
-- Keep only the hash in the database; give the original code to the participant.
insert into public.invitations (experiment_id, code_hash)
select id, encode(digest(upper('FIRST-TEST-CODE'), 'sha256'), 'hex')
from public.experiments
where name = 'Cognitive Style Research' and version = '0.1';
