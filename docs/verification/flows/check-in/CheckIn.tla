------------------------------- MODULE CheckIn -------------------------------
\* A journalist checking in while the app keeps the emergency alert current.
EXTENDS Naturals

VARIABLES pending, alert

vars == <<pending, alert>>

Init == pending = 0 /\ alert = "none"

YouCheckIn == pending < 3 /\ pending' = pending + 1 /\ UNCHANGED alert
ThirdCheckIn == pending = 3 /\ alert' = "updating" /\ pending' = 0
YouCheckInDuringUpdate == alert = "updating" /\ pending < 2 /\ pending' = pending + 1 /\ UNCHANGED alert
AlertReady == alert = "updating" /\ alert' = "current" /\ UNCHANGED pending
AlertFails == alert = "updating" /\ alert' = "stale" /\ UNCHANGED pending
ContactRequestsNow == alert \in {"none", "current", "stale"} /\ pending > 0 /\ alert' = "updating" /\ pending' = 0

Next == YouCheckIn \/ ThirdCheckIn \/ YouCheckInDuringUpdate \/ AlertReady \/ AlertFails \/ ContactRequestsNow

Spec == Init /\ [][Next]_vars

Bounded == pending <= 3
=============================================================================
