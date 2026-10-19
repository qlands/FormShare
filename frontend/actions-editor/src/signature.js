// Signature help: inside the parentheses of an API call, a line above the
// cursor with the call's arguments, the one being written in bold, and what
// the call does. The innermost call decides: inside String(…) within
// api.log(…), nothing is shown.

import {StateField} from "@codemirror/state";
import {showTooltip} from "@codemirror/view";
import {analyse} from "./analysis.js";

export function signatureAt(state, pos) {
  const a = analyse(state);
  for (let node = a.tree.resolveInner(pos, -1); node; node = node.parent) {
    if (node.name !== "ArgList") continue;
    const close = node.lastChild;
    const closed = !!close && close.name === ")" && close.to === node.to;
    if (pos <= node.from || (closed && pos >= node.to)) continue;
    const info = a.call(node.parent, false);
    if (!info || !info.spec || info.spec.type !== "method") return null;
    let index = 0;
    for (let c = node.firstChild; c && c.to <= pos; c = c.nextSibling) {
      if (c.name === ",") index++;
    }
    return {receiver: info.receiver, method: info.method, spec: info.spec, index: Math.min(index, Math.max(0, info.spec.args.length - 1)),
      prefix: prefixOf(a, info.receiver)};
  }
  return null;
}

function prefixOf(a, receiver) {
  const s = (a.run && a.run.s) || "s";
  const api = (a.run && a.run.api) || "api";
  return {s, api, row: "row", rows: "rows", case: api + ".case", parent: api + ".case.parent", lookupRow: "row"}[receiver.kind] || "";
}

function firstSentence(text) {
  const match = /^(.*?[.!?])(\s|$)/.exec(text || "");
  return match ? match[1] : text || "";
}

function tooltipFor(state) {
  const range = state.selection.main;
  if (!range.empty) return null;
  const sig = signatureAt(state, range.head);
  if (!sig) return null;
  return {
    pos: range.head,
    above: true,
    strictSide: false,
    arrow: false,
    create() {
      const dom = document.createElement("div");
      dom.className = "cm-actions-signature";
      const code = dom.appendChild(document.createElement("code"));
      code.appendChild(document.createTextNode(sig.prefix + "." + sig.method + "("));
      sig.spec.args.forEach((arg, i) => {
        if (i > 0) code.appendChild(document.createTextNode(", "));
        if (i === sig.index) code.appendChild(document.createElement("b")).textContent = arg.name;
        else code.appendChild(document.createTextNode(arg.name));
      });
      code.appendChild(document.createTextNode(")"));
      const doc = dom.appendChild(document.createElement("div"));
      doc.className = "cm-actions-signature-doc";
      doc.textContent = firstSentence(sig.spec.info);
      return {dom};
    },
  };
}

export const signatureHelp = StateField.define({
  create: state => tooltipFor(state),
  update(value, tr) {
    if (!tr.docChanged && !tr.selection) return value;
    return tooltipFor(tr.state);
  },
  provide: field => showTooltip.from(field),
});

