// The bundle's one global, FormShareActionsEditor: `create` makes an editor
// in the place of a textarea, `phrases` are the English messages a page may
// translate, and `testing` holds pure functions that run without a page, for
// the suite (formshare/tests/test_18_actions_editor.py runs the shipped
// bundle in Node).

import {EditorState} from "@codemirror/state";
import {javascript} from "@codemirror/lang-javascript";
import {createEditor, makeConfig, DEFAULT_PHRASES} from "./editor.js";
import {completeAt, compareCompletions} from "./completion.js";
import {diagnose} from "./lint.js";
import {signatureAt} from "./signature.js";
import {fullTree} from "./analysis.js";
import {closest} from "./model.js";

const stateOf = text => EditorState.create({doc: text, extensions: [javascript()]});

// The options as the list shows them before anything is typed.
const shown = (a, b) => ((a.section && a.section.rank) || 0) - ((b.section && b.section.rank) || 0) || compareCompletions(a, b);

const api = {
  version: "1.0.0",
  create: createEditor,
  phrases: DEFAULT_PHRASES,
  testing: {
    check(text, catalogue, phrases) {
      return diagnose(stateOf(text), makeConfig({catalogue, phrases})).map(d => [d.from, d.to, d.severity, d.message]);
    },
    complete(text, pos, catalogue, explicit) {
      const result = completeAt(stateOf(text), pos, makeConfig({catalogue}), !!explicit);
      if (!result) return null;
      const options = result.options.slice().sort(shown);
      return {
        from: result.from,
        to: result.to === undefined ? pos : result.to,
        labels: options.map(o => o.label),
        details: options.map(o => o.detail || ""),
        sections: options.map(o => (o.section ? o.section.name : "")),
      };
    },
    signature(text, pos) {
      const sig = signatureAt(stateOf(text), pos);
      if (!sig) return null;
      return {call: sig.prefix + "." + sig.method + "(" + sig.spec.args.map(arg => arg.name).join(", ") + ")",
        argument: sig.spec.args.length ? sig.spec.args[sig.index].name : null};
    },
    tree: text => fullTree(stateOf(text)).toString(),
    closest,
  },
};

(typeof window !== "undefined" ? window : globalThis).FormShareActionsEditor = api;
