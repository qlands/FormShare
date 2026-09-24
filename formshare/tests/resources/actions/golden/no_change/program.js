export default function run(s, api) {
  api.case.set("status", "pending");
  api.case.activate();
}
