-- Researcher participant-code visibility and recoverable session archiving.
-- Requires migrations 006 and 009.

alter table public.participant_sessions
  add column if not exists archived_at timestamptz,
  add column if not exists archived_by uuid;

comment on column public.participant_sessions.archived_at is
  'Soft-delete marker used by the researcher dashboard. Archived sessions and all related data remain intact.';

comment on column public.invitations.plaintext_code is
  'Researcher-visible invitation code. Retained after redemption and protected by researcher-only RPCs.';

-- Keep the readable code after successful redemption so the researcher can
-- associate the invitation with its participant session.
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

-- Return the complete participant directory, including archived sessions.
-- The browser receives this only after researcher authorization succeeds.
create or replace function public.researcher_participant_sessions()
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

  with response_counts as (
    select
      session_id,
      count(*) filter (where trial_kind = 'research')::integer as saved_test_answers,
      count(*) filter (where trial_kind = 'research' and subtest = 'analytic' and is_correct)::integer as correct_analytic_count,
      count(*) filter (where trial_kind = 'research' and subtest = 'wholistic' and is_correct)::integer as correct_wholistic_count
    from public.test_trial_responses
    group by session_id
  ), participant_rows as (
    select
      s.id as session_id,
      s.participant_id,
      s.current_phase,
      s.created_at,
      s.last_seen_at,
      s.completed_at,
      s.archived_at,
      s.archived_by,
      i.plaintext_code as invitation_code,
      i.status as invitation_status,
      i.expires_at as invitation_expires_at,
      coalesce(r.status, 'not_started') as test_status,
      coalesce(r.current_index, 0) as items_completed,
      r.analytic_median_ms,
      r.wholistic_median_ms,
      r.wholistic_analytic_ratio,
      r.started_at as test_started_at,
      r.completed_at as test_completed_at,
      coalesce(rc.saved_test_answers, 0) as saved_test_answers,
      coalesce(rc.correct_analytic_count, 0) as correct_analytic_count,
      coalesce(rc.correct_wholistic_count, 0) as correct_wholistic_count,
      coalesce(c.accepted, false) as consented,
      d.responses->>'age_range' as age_range,
      d.responses->>'education' as education
    from public.participant_sessions s
    join public.invitations i on i.id = s.invitation_id
    left join lateral (
      select pr.* from public.participant_test_runs pr
      where pr.session_id = s.id
      order by pr.started_at desc limit 1
    ) r on true
    left join response_counts rc on rc.session_id = s.id
    left join lateral (
      select co.accepted from public.consents co
      where co.session_id = s.id
      order by co.accepted_at desc limit 1
    ) c on true
    left join lateral (
      select dr.responses from public.demographic_responses dr
      where dr.session_id = s.id
      order by dr.submitted_at desc limit 1
    ) d on true
    order by s.created_at desc
  )
  select coalesce(jsonb_agg(to_jsonb(participant_rows)), '[]'::jsonb)
  into result
  from participant_rows;

  return result;
end;
$$;

revoke all on function public.researcher_participant_sessions() from public;
grant execute on function public.researcher_participant_sessions() to authenticated;

create or replace function public.researcher_set_session_archived(
  p_session_id uuid,
  p_archived boolean
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  changed_id uuid;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;

  update public.participant_sessions
  set archived_at = case when p_archived then coalesce(archived_at, now()) else null end,
      archived_by = case when p_archived then auth.uid() else null end
  where id = p_session_id
  returning id into changed_id;

  if changed_id is null then
    return jsonb_build_object('accepted', false, 'reason', 'session_not_found');
  end if;

  return jsonb_build_object('accepted', true, 'session_id', changed_id, 'archived', p_archived);
end;
$$;

revoke all on function public.researcher_set_session_archived(uuid, boolean) from public;
grant execute on function public.researcher_set_session_archived(uuid, boolean) to authenticated;

-- Optional SQL-Editor helper for an older session whose code was cleared by 009.
-- It updates only when the supplied code hashes to that session's invitation.
create or replace function public.backfill_session_invitation_code(
  p_session_id uuid,
  p_code text
)
returns boolean
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  normalized_code text := upper(trim(p_code));
begin
  update public.invitations i
  set plaintext_code = normalized_code
  from public.participant_sessions s
  where s.id = p_session_id
    and s.invitation_id = i.id
    and i.code_hash = encode(digest(normalized_code, 'sha256'), 'hex');

  return found;
end;
$$;

revoke all on function public.backfill_session_invitation_code(uuid, text) from public;
