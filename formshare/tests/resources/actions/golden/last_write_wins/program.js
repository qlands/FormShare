export default function run(s, api) {
  api.case.set("status", "first");
  api.case.set("status", "pending");
  api.case.set("trained", 1);
  api.case.set("trained", 0);
  api.case.activate();
  api.case.parent.set("closed", "no");
  api.case.parent.deactivate();
  api.case.parent.set("trained_teachers", api.case.parent.property("trained_teachers") * 2);
}
