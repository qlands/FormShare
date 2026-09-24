export default function run(s, api) {
  api.case.set("status", "visited");
  api.case.set("visits", api.case.property("visits") + 1);
  api.case.set("last_visit", api.now);
}
