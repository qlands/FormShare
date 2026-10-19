// The editor factory: a CodeMirror 6 editor in the place of the module's
// textarea. The textarea stays in the page, hidden, and always holds the
// current text, so that the form posts it and the page reads it as before;
// if the editor cannot be made, the textarea is left as it was.
//
// The package knows nothing of the page: what it needs comes in `options`.

import {EditorState, StateEffect, StateField} from "@codemirror/state";
import {
  EditorView, Decoration, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars,
  drawSelection, dropCursor, highlightActiveLine, placeholder, tooltips,
} from "@codemirror/view";
import {
  defaultHighlightStyle, syntaxHighlighting, indentOnInput, indentUnit, bracketMatching,
  foldGutter, foldKeymap,
} from "@codemirror/language";
import {defaultKeymap, history, historyKeymap, indentWithTab, isolateHistory} from "@codemirror/commands";
import {searchKeymap, highlightSelectionMatches} from "@codemirror/search";
import {autocompletion, closeBrackets, closeBracketsKeymap} from "@codemirror/autocomplete";
import {lintGutter, lintKeymap} from "@codemirror/lint";
import {javascript, javascriptLanguage} from "@codemirror/lang-javascript";
import {makeCatalogue} from "./model.js";
import {actionsCompletionSource, compareCompletions} from "./completion.js";
import {actionsLinter} from "./lint.js";
import {signatureHelp} from "./signature.js";
import {actionsTheme} from "./theme.js";

// English, for a page that passes no translation of a phrase. {name} and
// the like stand for what the message is about, by name, so that a
// translation may put them in any order. A page passes them as they are:
// FormShare's templates write {name} inside the msgid, since their _()
// fills nothing in.
export const DEFAULT_PHRASES = {
  source: "FormShare",
  syntax: "This part can't be read: check the brackets, quotes and operators around it.",
  noRun: "The module must export a default function run(s, api).",
  tooLarge: "The module is larger than {kb} KB.",
  noImports: "A module has no imports: what it reads comes in s and api.",
  onlyRun: "A module exports one thing: its default function run.",
  dynamicImport: "import() loads nothing: no host has a module loader.",
  await: "A module runs at once: nothing after an await runs.",
  newDate: "new Date() without arguments is not available: use api.now.",
  dateCall: "Date() is not available: use api.now.",
  dateNow: "Date.now is not available: use api.now.",
  mathRandom: "Math.random is not available: a run must give the same answer on every host.",
  codeFromText: "{name} is not available to a module.",
  locale: "{name} is not available: formatting is the module's own or api's.",
  timers: "{name} is not available: a module runs at once, with no timers.",
  absent: "{name} is not available to a module.",
  unknownQuestion: "This form has no question named “{name}”.",
  encryptedRead: "“{name}” is encrypted: the module reads its envelope, never the answer.",
  unknownApiMember: "api has no member “{name}”.",
  unknownCaseMember: "The case has no member “{name}”: read a property with property(\"…\") and a column with value(\"…\").",
  unknownParentMember: "The case's parent has no member “{name}”: read a property with property(\"…\") and a column with value(\"…\").",
  assignCase: "Assigning to the case changes nothing: use set(), activate() or deactivate().",
  noCase: "This form has no case: api.case is null.",
  noParent: "The case has no parent: api.case.parent is null.",
  unknownRepeat: "This form has no repeat named “{name}”.",
  nestedRepeat: "“{name}” is a repeat inside “{parent}”: read it from one of that repeat's rows, as row.repeat(\"…\").",
  unknownMulti: "This form has no multi-select named “{name}”.",
  notMulti: "“{name}” is not a multi-select, so this finds no code.",
  unknownChoice: "“{name}” has no choice “{code}”.",
  lookupApiName: "Name run's second parameter api: the server finds the lists to load by api.lookup(…).",
  lookupNotText: "Name the list as text, as in api.lookup(\"list\", code): the server loads only the lists named that way.",
  unknownList: "This form has no lookup list named “{name}”.",
  unknownRepeatColumn: "The repeat “{repeat}” has no column “{name}”.",
  unknownTarget: "The case has no property or column named “{name}”.",
  unknownParentTarget: "The case's parent has no property or column named “{name}”.",
  encryptedWrite: "“{name}” is encrypted: an action can only copy an envelope into it, not write an answer in clear.",
  unknownProperty: "The case has no property “{name}”.",
  unknownParentProperty: "The case's parent has no property “{name}”.",
  unknownColumn: "The case has no column “{name}”.",
  unknownParentColumn: "The case's parent has no column “{name}”.",
  didYouMean: "Did you mean “{name}”?",
  sectionQuestions: "Questions",
  sectionSubmission: "The submission",
  sectionColumns: "Columns",
  sectionRow: "The row",
  sectionProperties: "Properties",
  sectionCaseColumns: "Columns",
  typeText: "text",
  typeInteger: "integer",
  typeDecimal: "decimal",
  typeDate: "date",
  typeDatetime: "date and time",
  typeSelect: "select one",
  typeMulti: "multi-select",
  typeRepeat: "repeat",
  typeList: "lookup list",
  runSnippet: "the module's function",
};

const quietly = fn => (typeof fn === "function"
  ? (...args) => {
    try {
      return fn(...args);
    } catch (e) {
      if (typeof console !== "undefined") console.warn("actions editor:", e);
      return undefined;
    }
  }
  : null);

export function makeConfig(options = {}) {
  const phrases = Object.assign({}, DEFAULT_PHRASES);
  const given = options.phrases && typeof options.phrases === "object" ? options.phrases : {};
  for (const key of Object.keys(given)) {
    if (typeof given[key] === "string" && given[key] !== "") phrases[key] = given[key];
  }
  return {
    catalogue: makeCatalogue(options.catalogue),
    phrases,
    onChange: quietly(options.onChange) || (() => {}),
    onSave: quietly(options.onSave),
    onTest: quietly(options.onTest),
    ariaLabel: typeof options.ariaLabel === "string" ? options.ariaLabel : "",
    placeholder: typeof options.placeholder === "string" ? options.placeholder : "",
  };
}

// The line a dry run failed at, until the text changes.
const setFailedLine = StateEffect.define();
const failedLine = StateField.define({
  create: () => Decoration.none,
  update(marks, tr) {
    for (const effect of tr.effects) {
      if (!effect.is(setFailedLine)) continue;
      if (!effect.value) return Decoration.none;
      const line = tr.state.doc.line(effect.value.line);
      return Decoration.set([Decoration.line({class: "cm-actions-failed", attributes: {title: effect.value.message}}).range(line.from)]);
    }
    return tr.docChanged ? Decoration.none : marks;
  },
  provide: field => EditorView.decorations.from(field),
});

export function createEditor(textarea, options = {}) {
  const config = makeConfig(options);
  const host = document.createElement("div");
  host.className = "fs-actions-editor";
  textarea.parentNode.insertBefore(host, textarea.nextSibling);

  const keys = [];
  if (config.onSave) keys.push({key: "Mod-s", preventDefault: true, run: () => (config.onSave(), true)});
  if (config.onTest) keys.push({key: "Mod-Enter", preventDefault: true, run: () => (config.onTest(), true)});

  const extensions = [
    lineNumbers(),
    highlightActiveLineGutter(),
    foldGutter(),
    lintGutter(),
    highlightSpecialChars(),
    history(),
    drawSelection(),
    dropCursor(),
    EditorState.allowMultipleSelections.of(true),
    indentOnInput(),
    indentUnit.of("  "),
    syntaxHighlighting(defaultHighlightStyle, {fallback: true}),
    bracketMatching(),
    closeBrackets(),
    highlightActiveLine(),
    highlightSelectionMatches(),
    autocompletion({maxRenderedOptions: 500, compareCompletions}),
    javascript(),
    javascriptLanguage.data.of({autocomplete: actionsCompletionSource(config)}),
    actionsLinter(config),
    signatureHelp,
    failedLine,
    actionsTheme,
    config.placeholder ? placeholder(config.placeholder) : [],
    // Tooltips in <body>, so that no container clips them.
    tooltips({parent: document.body}),
    // Tab indents, as in any code editor; Escape and then Tab leaves.
    keymap.of([...keys, ...closeBracketsKeymap, ...defaultKeymap, ...searchKeymap, ...historyKeymap,
      ...foldKeymap, ...lintKeymap, indentWithTab]),
    // Code is not prose: no spelling, corrections or writing assistants.
    EditorView.contentAttributes.of(Object.assign({
      spellcheck: "false", autocorrect: "off", autocapitalize: "off",
      "data-gramm": "false", "data-gramm_editor": "false", "data-enable-grammarly": "false",
    }, config.ariaLabel ? {"aria-label": config.ariaLabel} : {})),
    EditorView.updateListener.of(update => {
      if (!update.docChanged) return;
      textarea.value = update.state.doc.toString();
      config.onChange(textarea.value);
    }),
  ];
  const stateFor = text => EditorState.create({doc: text, extensions});

  let view;
  try {
    view = new EditorView({parent: host, state: stateFor(textarea.value || "")});
  } catch (e) {
    host.remove();
    throw e;
  }
  textarea.style.display = "none";

  return {
    getValue: () => view.state.doc.toString(),
    // A new text with a fresh undo history.
    setValue(text) {
      textarea.value = text;
      view.setState(stateFor(text));
    },
    // A new text as one edit, which Ctrl+Z takes back.
    replace(text) {
      view.dispatch({
        changes: {from: 0, to: view.state.doc.length, insert: text},
        selection: {anchor: 0},
        annotations: isolateHistory.of("full"),
        userEvent: "input.replace",
      });
      view.scrollDOM.scrollTop = 0;
    },
    // A line the server reported, marked until the text changes. Only the
    // editor scrolls to it, not the page.
    markLine(number, message) {
      const doc = view.state.doc;
      const n = Math.max(1, Math.min(doc.lines, Math.floor(Number(number)) || 1));
      view.dispatch({effects: setFailedLine.of({line: n, message: String(message || "")})});
      view.requestMeasure({
        read: v => v.lineBlockAt(doc.line(n).from).top,
        write: (top, v) => {
          v.scrollDOM.scrollTop = Math.max(0, top - v.scrollDOM.clientHeight / 3);
        },
      });
    },
    clearMark: () => view.dispatch({effects: setFailedLine.of(null)}),
    focus: () => view.focus(),
    // Measure again once visible.
    refresh: () => view.requestMeasure(),
    destroy() {
      view.destroy();
      host.remove();
      textarea.style.display = "";
    },
  };
}
