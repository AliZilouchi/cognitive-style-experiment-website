-- Keeps pgcrypto helpers available inside the security-definer function.
-- This migration preserves all invitations and participant sessions.

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
