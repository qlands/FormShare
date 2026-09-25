export default function run(s, api) {
  if (api.case === null) { return; }
  // Row 1: when days since case last_visit is greater than 20, set property status of the case to 'overdue'
  if ((api.case.property("last_visit") === null ? null : api.days(api.case.property("last_visit"), api.now)) !== null && (api.case.property("last_visit") === null ? null : api.days(api.case.property("last_visit"), api.now)) > 20) { api.case.set("status", "overdue"); }
  // Row 2: when days since case last_visit is at most 20, set property status of the case to 'recent'
  else if ((api.case.property("last_visit") === null ? null : api.days(api.case.property("last_visit"), api.now)) !== null && (api.case.property("last_visit") === null ? null : api.days(api.case.property("last_visit"), api.now)) <= 20) { api.case.set("status", "recent"); }
}
