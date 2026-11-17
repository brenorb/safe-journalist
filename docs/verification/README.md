# Check-in coverage verification

| Skill | What it checks | Tool |
| --- | --- | --- |
| [verify-check-in-coverage](../../.claude/skills/verify-check-in-coverage/SKILL.md) | Every check-in is stored and reaches an emergency summary | TLA+ / TLC, 1,499 states, plus `tests/test_entry_coverage.py` |

The model found two ways a check-in could miss the emergency contacts, now fixed:

1. Two check-ins in the same second had the same file name, so the second replaced the first (50f7e3f).
2. A check-in written while a summary was being generated was older than that summary's name, so no summary ever included it (ea136bc).

## Check in and keep the alert current

Generated with pstack `/statechart` from [CheckIn.tla](flows/check-in/CheckIn.tla) ([TLC report](flows/check-in/report.md)). The alert and the waiting check-ins are parallel regions.

```mermaid
---
title: "Check in and keep the alert current"
---
stateDiagram-v2
  direction LR
  state "At the same time" as all {
    state "Alert" as r0 {
      s0: No alert yet
      s1: Alert being written
      s2: Alert current
      s3: Alert out of date
      [*] --> s0
      s0 --> s1: someone presses summarize now [unless Nothing new]
      s1 --> s2: the AI returns the alert
      s1 --> s3: the AI call fails
      s0 --> s1: the third new check-in starts an update [when Three new check-ins]
      s2 --> s1: someone presses summarize now [unless Nothing new]
      s3 --> s1: someone presses summarize now [unless Nothing new]
      s2 --> s1: the third new check-in starts an update [when Three new check-ins]
      s3 --> s1: the third new check-in starts an update [when Three new check-ins]
    }
    --
    state "CheckIns" as r1 {
      s4: Nothing new
      s5: New check-ins waiting
      s6: Three new check-ins
      [*] --> s4
      s4 --> s5: you check in
      s5 --> s4: someone presses summarize now [unless Alert being written]
      s4 --> s5: you check in during the update [when Alert being written]
      s5 --> s6: you check in
      s6 --> s4: someone presses summarize now [unless Alert being written]
      s6 --> s4: the third new check-in starts an update
    }
  }
```
