export default function run(s, api) {
  api.case.set("visits", 6 / 2);
  api.case.set("score", 2.50);
  api.case.set("note", String(0.1 + 0.2) + " " + String(1e21) + " " + String(-0.5));
  api.case.set("last_visit", api.now);
}
