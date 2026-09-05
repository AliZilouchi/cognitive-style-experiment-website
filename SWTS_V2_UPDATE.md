# SWTS conversation-centred v2

This package changes the three SWTS tasks from final-answer assignments into conversation-centred information-seeking situations.

## Included changes

- Shared Borlund source-of-need and environment across all three tasks
- Distinct task problems and objectives for factual exploration, comparison, and integrated understanding
- Task-specific short closing reflections instead of deliverable-style final answers
- Updated pre-task, post-task, comparative, Think Aloud, chat, preview, and researcher-dashboard wording
- Progressive-disclosure RAG policy shared by all task IDs
- Deterministic clarification for plainly incomplete messages
- SWTS version `sepid-island-fa-swts-v2`

## Database step

After deploying the code, run this file once in Supabase SQL Editor:

```text
supabase/011_swts_conversation_centered_v2.sql
```

Existing SWTS runs retain their original version. Fresh participant runs are labelled v2.

## Deployment

Redeploy both parts from this package:

1. The website/frontend project
2. The RAG backend, because `prompts.py` and `graph.py` changed

No environment-variable change is required.
