export default function run(s, api) {
  api.case.set("score", api.avg(s.repeat("rpt_trees"), "tree_height"));
}
