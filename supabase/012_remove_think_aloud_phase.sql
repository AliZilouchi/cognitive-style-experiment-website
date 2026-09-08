-- Think-aloud is no longer part of the participant flow. Preserve historical
-- responses, but move any unfinished session stranded on that phase forward.
update public.participant_sessions
set current_phase = 'pre_task',
    updated_at = now()
where current_phase = 'think_aloud'
  and completed_at is null;
