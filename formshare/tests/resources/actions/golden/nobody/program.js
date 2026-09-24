export default function run(s, api) {
  if (s.repeat("rpt_visits").length === 0) { api.case.set("status", "lost"); }
}
