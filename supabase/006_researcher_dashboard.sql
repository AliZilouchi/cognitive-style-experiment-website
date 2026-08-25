-- Protected researcher dashboard for the Cognitive Style Research Platform.
-- Run this migration once in Supabase SQL Editor.

create table if not exists public.researcher_accounts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

alter table public.researcher_accounts enable row level security;
revoke all on public.researcher_accounts from anon, authenticated;

create or replace function public.is_active_researcher()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.researcher_accounts r
    where r.user_id = auth.uid() and r.active
  );
$$;

revoke all on function public.is_active_researcher() from public;
grant execute on function public.is_active_researcher() to authenticated;

-- Deliberately not granted to browser roles. Run it only from SQL Editor after
-- creating the researcher in Authentication > Users.
create or replace function public.register_researcher(
  p_email text,
  p_display_name text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  matched_user auth.users%rowtype;
begin
  select * into matched_user
  from auth.users
  where lower(email) = lower(trim(p_email))
  order by created_at desc
  limit 1;

  if not found then
    return jsonb_build_object('accepted', false, 'reason', 'auth_user_not_found');
  end if;

  insert into public.researcher_accounts (user_id, email, display_name, active)
  values (matched_user.id, matched_user.email, nullif(trim(p_display_name), ''), true)
  on conflict (user_id) do update
    set email = excluded.email,
        display_name = excluded.display_name,
        active = true;

  return jsonb_build_object(
    'accepted', true,
    'user_id', matched_user.id,
    'email', matched_user.email
  );
end;
$$;

revoke all on function public.register_researcher(text, text) from public;

create or replace function public.researcher_dashboard()
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
  select jsonb_build_object(
    'summary', jsonb_build_object(
      'total_sessions', (select count(*) from public.participant_sessions),
      'active_sessions', (select count(*) from public.participant_sessions where completed_at is null),
      'completed_tests', (select count(*) from public.participant_test_runs where status = 'completed'),
      'unused_invitations', (select count(*) from public.invitations where status = 'unused' and (expires_at is null or expires_at > now()))
    ),
    'participants', coalesce((select jsonb_agg(to_jsonb(participant_rows)) from participant_rows), '[]'::jsonb)
  ) into result;

  return result;
end;
$$;

revoke all on function public.researcher_dashboard() from public;
grant execute on function public.researcher_dashboard() to authenticated;

create or replace function public.researcher_trial_details(p_session_id uuid)
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

  select coalesce(jsonb_agg(to_jsonb(t) order by t.trial_index), '[]'::jsonb)
  into result
  from (
    select
      tr.trial_id,
      tr.trial_index,
      tr.trial_kind,
      tr.subtest,
      tr.response_value,
      tr.correct_answer,
      tr.is_correct,
      tr.reaction_time_ms,
      tr.page_hidden,
      tr.focus_lost_count,
      tr.input_method,
      tr.client_created_at,
      tr.server_received_at
    from public.test_trial_responses tr
    where tr.session_id = p_session_id
  ) t;

  return result;
end;
$$;

revoke all on function public.researcher_trial_details(uuid) from public;
grant execute on function public.researcher_trial_details(uuid) to authenticated;

create or replace function public.researcher_export_trials()
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

  select coalesce(jsonb_agg(to_jsonb(t) order by t.participant_id, t.trial_index), '[]'::jsonb)
  into result
  from (
    select
      s.participant_id,
      tr.test_version,
      tr.trial_id,
      tr.trial_index,
      tr.trial_kind,
      tr.subtest,
      tr.response_value,
      tr.correct_answer,
      tr.is_correct,
      tr.reaction_time_ms,
      tr.page_hidden,
      tr.focus_lost_count,
      tr.input_method,
      tr.client_created_at,
      tr.server_received_at
    from public.test_trial_responses tr
    join public.participant_sessions s on s.id = tr.session_id
  ) t;

  return result;
end;
$$;

revoke all on function public.researcher_export_trials() from public;
grant execute on function public.researcher_export_trials() to authenticated;

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
  created_invitation public.invitations%rowtype;
begin
  if not public.is_active_researcher() then
    raise exception 'researcher_access_required' using errcode = '42501';
  end if;

  if nullif(trim(p_code), '') is null or length(trim(p_code)) < 6 then
    return jsonb_build_object('accepted', false, 'reason', 'code_too_short');
  end if;

  insert into public.invitations (experiment_id, code_hash, expires_at)
  select e.id, encode(digest(upper(trim(p_code)), 'sha256'), 'hex'), p_expires_at
  from public.experiments e
  where e.name = 'Cognitive Style Research' and e.version = '0.1'
  returning * into created_invitation;

  if created_invitation.id is null then
    return jsonb_build_object('accepted', false, 'reason', 'experiment_not_found');
  end if;

  return jsonb_build_object(
    'accepted', true,
    'invitation_id', created_invitation.id,
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
