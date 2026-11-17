------------------------------ MODULE CheckIns ------------------------------
\* Check-ins (POST /entries -> storage.write_entry) and the background
\* summary (summarizer.generate_summary) on one data directory, with a clock
\* in ticks. Several check-ins may land in one tick.
\*   CheckIn(i) -> create_entry: name the entry with generate_timestamp()
\*   Tick       -> time passes
\*   Read       -> generate_summary lists the entries newer than the last
\*                 summary's name and sends them to the AI
\*   Finish     -> the AI answers; write_summary names the summary
\* Broken = TRUE is the code before the fix: one-second names, so a second
\* check-in in the same tick replaced the first, and the summary was named
\* when the AI answered instead of when it read the entries.
EXTENDS Naturals, FiniteSets

CONSTANT Broken

Ids == 1..3
MaxTick == 2

VARIABLES now, stored, written, lastName, readAt, covered, pc

vars == <<now, stored, written, lastName, readAt, covered, pc>>

Init ==
  /\ now = 0 /\ stored = {} /\ written = {}
  /\ lastName = 0 /\ readAt = 0 /\ covered = {} /\ pc = "idle"

\* stored holds <<id, tick>>; the old names collided on the tick.
CheckIn(i) ==
  /\ i \notin written
  /\ written' = written \cup {i}
  /\ stored' = IF Broken
               THEN {e \in stored : e[2] # now} \cup {<<i, now>>}
               ELSE stored \cup {<<i, now>>}
  /\ UNCHANGED <<now, lastName, readAt, covered, pc>>

Tick == now < MaxTick /\ now' = now + 1 /\ UNCHANGED <<stored, written, lastName, readAt, covered, pc>>

\* Entries strictly newer than the last summary's name; ties at a name were
\* written before that summary read them, as the microsecond names ensure.
Read ==
  /\ pc = "idle"
  /\ covered' = covered \cup {e[1] : e \in {x \in stored : x[2] >= lastName}}
  /\ readAt' = now /\ pc' = "calling"
  /\ UNCHANGED <<now, stored, written, lastName>>

Finish ==
  /\ pc = "calling"
  /\ lastName' = IF Broken THEN now ELSE readAt
  /\ pc' = "idle"
  /\ UNCHANGED <<now, stored, written, readAt, covered>>

Next == Tick \/ Read \/ Finish \/ \E i \in Ids : CheckIn(i)

Spec == Init /\ [][Next]_vars

\* Every check-in the journalist sent is still stored.
NoCheckInLost == {e[1] : e \in stored} = written

\* A check-in older than the last summary's name was in some summary, so it
\* reached the emergency contacts.
EveryCheckInReachesAnAlert ==
  pc = "idle" => \A e \in stored : e[2] < lastName => e[1] \in covered
=============================================================================
