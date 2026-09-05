# Island knowledge, SWTS context, and response-verifier update

This consolidated patch adds nine missing island-information areas, supplies
the active SWTS problem/objective on every experiment turn, and adds a second
grounding pass using the same configured language model.

## Apply

Extract this ZIP at the repository root and allow it to overwrite files with
the same relative paths. Then commit and push the extracted files.

Both the RAG/backend and frontend deployments must be rebuilt. The frontend
change removes a stale hard-coded 29-source readiness check. The Supabase
schema and environment variables do not change.

## Behaviour

- Free chat can use the complete corpus without an experiment-task boundary.
- Experiment chat receives the shared scenario plus the current task's problem,
  objective, core scope, and adjacent scope.
- Out-of-scope questions are answered briefly when the corpus supports them,
  followed by a neutral reminder of the current task. The assistant does not
  prescribe a next question or make the participant's final choice.
- New atomic retrieval units cover language, healthcare, general conditions,
  crowding, visitor feedback, migration, safety, arrival, and governance.
- The first model pass drafts the answer. A second pass with the same model
  checks factual support, calculations, scope, completeness, and unnecessary
  disclosure, then returns a corrected participant-facing answer.
- If the verifier call itself fails, the API returns the draft instead of
  trapping the participant in a loading loop and reports that fallback in the
  response metadata.

## Configuration

The verifier is enabled by default and needs no new environment variable. For
diagnostic comparison only, it can be disabled with:

```text
ENABLE_RESPONSE_VERIFIER=false
```

Keep it enabled during the study. Enabling it uses two chat-model calls per
participant message and therefore increases model cost and response latency.

## Verify locally

```bash
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -p "test_*.py"
```

Expected result: 43 tests pass.
