export default function run(s, api) {
  api.case.set("note", s.head_name);
  api.case.set("status", api.user);
  api.log("copied " + api.lookup("crop_list", "c1").crop_list_des);
}
