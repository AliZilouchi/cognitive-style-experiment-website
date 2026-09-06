# Model pipeline + researcher scenario lab (v11)

Copy this folder over the root of `cognitive-style-experiment-website`, preserving paths.

## What changes

- Hybrid semantic + lexical retrieval for names and exact facts.
- Separate retrieval for explicit multi-part questions, fused into one bounded evidence set.
- Context resolution for follow-ups such as «حالا جواب بده».
- Social turns such as «سلام» and «ممنون» bypass RAG.
- Task reminders appear only after sustained topic drift.
- Stronger evidence verifier for unsupported value judgments.
- Researcher-only scenario lab with editable scenarios and ordered questions.
- The lab runs the real `/api/rag/chat` path with conversation history.
- Lab scenarios and results are memory-only and disappear on page exit/reload.

Permanent default scenarios are configured in:

`app/model-evaluation-scenarios.ts`

## Deployment

No SQL migration, dependency, or new environment variable is required.

Commit all included files, push once, then redeploy both Vercel projects from the same commit:

1. RAG backend project (because `backend/` changed).
2. Website/frontend project (because `app/` changed).

## Validation completed

- 60 backend tests passed.
- TypeScript typecheck passed.
- Next.js production build passed.
