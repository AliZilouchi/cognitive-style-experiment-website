# Post-retrieval Knowledge Index v12

Copy the contents of this folder over the repository root, preserving paths.

## New pipeline

1. Deterministic preprocessor for social messages, normalization, follow-up context, and explicit question splitting.
2. Open hybrid retrieval using the configured `TOP_K` ceiling.
3. LLM evidence judge after retrieval: coverage decision, noise removal, Request Level, and generator instruction.
4. Answer generator using only selected evidence.
5. Final verifier.

The former pre-retrieval Knowledge Index no longer blocks unknown aliases. A question such as «جشن یا رویداد چه زمانی است؟» reaches retrieval before support is decided.

## Retrieval changes

- Curated `fact` and `comparison` chunks receive a small rank bonus.
- `SOURCE-FALLBACK` chunks receive a small penalty but remain available.
- Multi-part retrieval reserves at least one candidate for each explicit sub-question.
- The post-retrieval judge selects at most six final evidence chunks.

## Researcher model lab

The lab now displays:

- evidence-judge status;
- coverage/gap explanation;
- only the evidence selected for answer generation.

All lab state remains memory-only.

## Deployment

- Keep backend `TOP_K=8`.
- No SQL migration, dependency, or new environment variable is required.
- Redeploy the RAG backend and frontend from the same commit.

## Important time-limit note

This update intentionally does not contain or modify `app/swts-config.ts`. The existing one-hour SWTS time limit remains unchanged.

## Validation

- 61 backend tests passed.
- TypeScript typecheck passed.
- Next.js production build passed.
