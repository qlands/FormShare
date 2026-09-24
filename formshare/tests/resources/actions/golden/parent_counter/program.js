export default function run(s, api) {
  const trained = s.trained === "yes" && s.years_experience >= 3;
  api.case.set("status", "interviewed");
  api.case.set("trained", trained ? 1 : 0);
  if (trained) { api.case.parent.set("trained_teachers", api.case.parent.property("trained_teachers") + 1); }
}
