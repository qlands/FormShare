export default function run(s, api) {
  api.log("before");
  api.case.set("status", "never applied");
  if (s.hh_size > 3) {
    throw new Error("a household of " + s.hh_size + " is not expected");
  }
}
