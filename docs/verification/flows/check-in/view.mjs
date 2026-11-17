export const title = "Check in and keep the alert current";
export const state = (v) => ({
  Alert: { none: "No alert yet", updating: "Alert being written", current: "Alert current", stale: "Alert out of date" }[v.alert],
  CheckIns: v.pending === 0 ? "Nothing new" : v.pending < 3 ? "New check-ins waiting" : "Three new check-ins",
});
const steps = {
  YouCheckIn: "you check in",
  ThirdCheckIn: "the third new check-in starts an update",
  YouCheckInDuringUpdate: "you check in during the update",
  AlertReady: "the AI returns the alert",
  AlertFails: "the AI call fails",
  ContactRequestsNow: "someone presses summarize now",
};
export const step = (action) => steps[action] ?? null;
