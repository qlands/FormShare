export default function run(s, api) {
  // Every tree of every plot: a repeat inside a repeat, read row by row.
  var trees = [];
  s.repeat("rpt_plots").forEach(function (plot) { trees = trees.concat(plot.repeat("rpt_trees")); });
  api.case.set("score", api.max(trees, "tree_height"));
  api.case.set("visits", api.count(trees, "tree_height"));
  var used = s.repeat("rpt_plots").filter(function (plot) { return plot.selected("plot_uses", "u3"); });
  api.log(used.map(function (plot) { return plot.plot_name + " " + plot.selections("plot_uses").join("+"); }).join(", "));
  api.log([api.sum(s.repeat("rpt_plots"), "plot_area"), api.avg(trees, "tree_height"), api.min(trees, "tree_height"),
           api.days("2026-02-04", api.now), trees[3].parent_rowuuid, s.repeat("rpt_plots")[2].repeat("rpt_trees").length].join(" "));
}
