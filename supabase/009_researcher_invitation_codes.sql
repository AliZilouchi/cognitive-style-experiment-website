-- Retain newly created invitation codes for the protected researcher dashboard.
-- Redemption still uses the hash; plaintext is erased as soon as a code is used.

alter table public.invitations
  add column if not exists plaintext_code text;

comment on column public.invitations.plaintext_code is
  'Researcher-visible code for an unused invitation; cleared immediately on redemption.';

create or replace function public.redeem_invitation(invitation_code text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
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
  set status = 'started', started_at = now(), plaintext_code = null
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

create or replace function public.researcher_create_invitation(
  p_code text,
  p_expires_at timestamptz default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  normalized_code text := upper(trim(p_code));
  created_invitation public.invitations%rowtype;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;

  if nullif(normalized_code, '') is null or length(normalized_code) < 6 then
    return jsonb_build_object('accepted', false, 'reason', 'code_too_short');
  end if;

  insert into public.invitations (experiment_id, code_hash, plaintext_code, expires_at)
  select e.id, encode(digest(normalized_code, 'sha256'), 'hex'), normalized_code, p_expires_at
  from public.experiments e
  where e.name = 'Cognitive Style Research' and e.version = '0.1'
  returning * into created_invitation;

  if created_invitation.id is null then
    return jsonb_build_object('accepted', false, 'reason', 'experiment_not_found');
  end if;

  return jsonb_build_object(
    'accepted', true,
    'invitation_id', created_invitation.id,
    'code', created_invitation.plaintext_code,
    'status', created_invitation.status,
    'expires_at', created_invitation.expires_at,
    'created_at', created_invitation.created_at
  );
exception
  when unique_violation then
    return jsonb_build_object('accepted', false, 'reason', 'code_already_exists');
end;
$$;

revoke all on function public.researcher_create_invitation(text, timestamptz) from public;
grant execute on function public.researcher_create_invitation(text, timestamptz) to authenticated;

-- SQL-Editor-only helper, retained for manual invitation creation.
create or replace function public.create_study_invitation(p_code text, p_expires_at timestamptz default null)
returns table (invitation_id uuid, invitation_status text, created_at timestamptz)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  normalized_code text := upper(trim(p_code));
begin
  if nullif(normalized_code, '') is null then
    raise exception 'Invitation code cannot be empty';
  end if;

  return query
  insert into public.invitations (experiment_id, code_hash, plaintext_code, expires_at)
  select e.id, encode(digest(normalized_code, 'sha256'), 'hex'), normalized_code, p_expires_at
  from public.experiments e
  where e.name = 'Cognitive Style Research' and e.version = '0.1'
  returning invitations.id, invitations.status, invitations.created_at;
end;
$$;

revoke all on function public.create_study_invitation(text, timestamptz) from public;

create or replace function public.researcher_list_invitation_codes()
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

  select coalesce(jsonb_agg(to_jsonb(item) order by item.created_at desc), '[]'::jsonb)
  into result
  from (
    select id, plaintext_code as code, status, created_at, expires_at
    from public.invitations
    where status = 'unused' and plaintext_code is not null
    order by created_at desc
    limit 100
  ) item;

  return result;
end;
$$;

revoke all on function public.researcher_list_invitation_codes() from public;
grant execute on function public.researcher_list_invitation_codes() to authenticated;
