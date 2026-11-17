---
name: verify-check-in-coverage
description: Check that every check-in the journalist sends is stored and reaches an emergency-contact summary, even when check-ins arrive in the same second or while a summary is being generated. Use when changing generate_timestamp, write_entry, list_entries or count_entries_since_last_summary in storage.py, generate_summary in summarizer.py, or create_entry and run_summarization in api.py.
---

# Verify check-in coverage

**Properties.** `NoCheckInLost`: every check-in sent is still stored. `EveryCheckInReachesAnAlert`: a check-in older than the latest summary's name was included in some summary.

**Harm if broken.** The emergency contacts read an alert that leaves out what the journalist reported, possibly the most urgent part.

## Run

```sh
export TLA2TOOLS=/absolute/path/to/tla2tools.jar   # TLC 1.7.4 release
export JAVA=/path/to/java                          # Java 11 or later
bash scripts/verification/check-model.sh .claude/skills/verify-check-in-coverage/model/CheckIns.tla
bash scripts/verification/check-model.sh .claude/skills/verify-check-in-coverage/model/CheckIns.tla --mutant
uv run --extra dev pytest -q tests/test_entry_coverage.py
```

The model must pass (1,499 distinct states: three check-ins, two ticks, any number of summaries). The `--mutant` run replays the code before commits 50f7e3f and ea136bc and must report a violation. With one rule per config, `NoCheckInLost` fails on two check-ins in one tick, and `EveryCheckInReachesAnAlert` on a check-in written between `Read` and `Finish`. `tests/test_entry_coverage.py` replays both on the real code, with the AI call mocked. Read every TLC result with the pstack `/statechart` skill.

## Coverage

Synced with the code at commit `ea136bc`. Move this forward only after you confirm that the model still describes the code at the new commit.

| Model step | Code (`src/safe_journalist/`) |
| --- | --- |
| `CheckIn` | `api.create_entry` → `storage.generate_timestamp`, `storage.write_entry` |
| `Read` | `summarizer.generate_summary` up to `encrypted_openai_call` |
| `Finish` | `storage.write_summary` with the timestamp taken before the read |

The model counts time in ticks. It reads entries at the summary's own tick as new, which stands for the microsecond names that make a tie impossible in practice.

## Not covered

Two summaries running at once (the count trigger can start a second background task while one is in flight), AI failures, the Maple session and encryption, and the existing `test_generate_summary_constructs_correct_prompt_format` failure, which predates this work.
