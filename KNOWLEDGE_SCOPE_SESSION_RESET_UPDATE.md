# Knowledge scope and reusable-browser session update

This patch is applied **after** `cognitive-style-rag-major-discipline-update-v2`.

## What changes

- Adds a machine-readable island knowledge index.
- Returns a fixed unavailable response for topics outside the defined world.
- Searches normally for supported topics and distinguishes undocumented details
  from explicitly unavailable services.
- Adds a complete closed-world service matrix for the five accommodations.
- Prevents the assistant from turning multi-person/multi-day price questions
  into budget calculations while preserving documented prices and comparisons.
- Classifies each supported topic as core, adjacent, or outside the current SWTS
  task. Outside-task answers receive a deterministic neutral task reminder.
- Adds a completion-page action that safely clears participant-local state and
  returns the same browser to the invitation screen for a new participant.
- Associates queued events with their original session so records cannot cross
  into the next participant session.

## Apply and deploy

Extract at the repository root, overwrite matching files, commit, and push.
Redeploy both the backend and frontend Vercel projects. No Supabase migration or
new environment variable is required.

## Verification

```bash
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -p "test_*.py"
npm run typecheck
npm run build
```

Expected result: 51 backend tests pass and the Next.js production build succeeds.
