export default function run(s, api) {
  var c3 = api.lookup("crop_list", "c3");
  api.log(JSON.stringify(c3));
  api.log(String(api.lookup("crop_list", "c9")));
  api.log([s.rowuuid, s.submittedBy, s.submittedDate, s.selections("crops").join("+"), s.selected("crops", "c2"),
           s.head_name, typeof s.hh_size, api.user].join(" | "));
  if (c3 && c3.crop_list_group === "cereal") { api.case.set("note", "grows cereal"); }
}
