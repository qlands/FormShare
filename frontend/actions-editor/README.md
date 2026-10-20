# The actions editor

The code editor of a form's actions written in code ("Add an action (Expert
mode)", `formshare/templates/dashboard/projects/case_management/action_code.jinja2`),
and the read-only view of an action's code on its test page
(`action_test.jinja2`).
It is CodeMirror 6 with FormShare's actions API
(`docs/formshare_case_management/actions-api.md`), built the way the Form
Builder plugin built its XPath editor (`CODEMIRROR_INTEGRATION.md` in that
plugin), with JavaScript's own grammar instead of a new one.

The page runs the bundle this package builds,
`formshare/jsandcss/js/plugins/codemirror6/actions_editor.min.js` (resource
`actions_editor`), never `src/`. **Rebuild it and commit it with any change
to `src/`.**

## What the owner gets

- **Code.** JavaScript colours, line numbers, folding, matching brackets,
  closing quotes and brackets, indenting on Enter, search (Ctrl+F), and an
  undo history of its own.
- **Completion.**
  - After `s.`: the questions in form order, then the submission's members.
  - After `api.`, `api.case.` and `api.case.parent.`: their members.
  - After a repeat's row: the repeat's columns. A row is one bound by
    `for (const m of s.repeat("meals"))` or by a callback of `forEach`, `map`,
    `filter` and the like.
  - Inside quotes, the names an argument takes:
    - a property or column to `set`;
    - a repeat;
    - a multi-select and then its choices;
    - a lookup list;
    - a repeat's column in `api.avg(s.repeat("…"), "…")`.
  - The choices of a select compared with `===`, or in a `switch`.
  - A module without its function is offered
    `export default function run(s, api)`.
  - Picking a method puts the cursor in its parentheses, or in its quotes,
    with their list open. Picking a name moves on to the next argument.
- **Signature help** inside an API call, with the argument being written in
  bold.
- **Checks while typing.** Each says what the server would do, and only
  where that is certain (a false alarm costs more than a miss).
  - *Errors* are what refuses or fails the module:
    - what `load_module` refuses when it is saved: no
      `export default function run`, or more than 64 KB;
    - what every host's prelude refuses when it runs: `Date.now`,
      `new Date()`, `Date()`, `Math.random`, `eval`, `Function`, the locale
      functions, timers, `import`;
    - what the server cannot apply: `set` of a name that is neither a
      property nor a column, or of an encrypted column; `property` or `value`
      of what the case lacks; a lookup list the form lacks.
  - *Warnings* are what runs but cannot be what was meant:
    - a question, repeat, multi-select or choice the form lacks;
    - a repeat read from `s` that lives inside another repeat;
    - an assignment to the case;
    - `await`;
    - a list not named as text.
- **Keys.**
  - Ctrl+Space: completion.
  - Ctrl+S saves and Ctrl+Enter tests with the chosen submission (the page's
    `onSave` and `onTest`).
  - Tab indents. Escape and then Tab leaves the editor.
- **A dry run's failure** marks the line the server named (`markLine`),
  until the text changes.

## How a page uses it

```js
var editor = FormShareActionsEditor.create(textarea, {
  catalogue: …,          // catalogue_for_editor, printed by the view
  phrases: {…},          // translations; English by default
  onSave: fn, onTest: fn, onChange: fn,
  ariaLabel: "…", placeholder: "…",
  readOnly: true,        // shown, not written (the test page)
  minHeight: "60px"      // instead of 380px, for short code
});
// editor.getValue(), setValue(text), replace(text), markLine(n, message),
// clearMark(), problems(), focus(), refresh(), destroy()
```

- **The textarea stays.** It is hidden and always holds the text, so the
  form posts it and the page reads it as before.
- **Without the editor,** the page keeps the textarea: when the bundle is
  missing or `create` throws.

**The catalogue.** `catalogue_for_editor` in
`formshare/processes/db/actions.py` gives the names a run meets:

| Key | What it holds |
|---|---|
| `known` | false for a form with no repository; then no name is checked |
| `questions` | `{name, type, label, select, multi, choices, encrypted, system}` |
| `repeats` | `{name, parent, columns}` |
| `case`, `parent` | `{table, properties, columns}`, or null |
| `lookups` | `{name, columns}` |

**The phrases.** The English is `DEFAULT_PHRASES` in `src/editor.js`. Each
phrase names what it is about as `{name}`, `{code}` and the like, so that a
translation may reorder them. The template passes `_()` of the same text with
`{name}` inside the msgid: a FormShare template's `_()` fills nothing in.
`test_18` keeps the template's English equal to the bundle's.

## Building and testing

```bash
cd frontend/actions-editor
npm install      # once; node_modules is not in git
npm test         # node --test test/, against the source
npm run build    # the bundle and THIRD_PARTY_LICENSES.txt
```

- **The build.** esbuild writes one IIFE that sets one global,
  `FormShareActionsEditor`, ES2020, minified. `tools/licenses.mjs` lists every
  bundled package and its licence, all MIT, from esbuild's metafile.
- **No server restart for a new bundle,** which is a static file. A change to
  `catalogue_for_editor` needs one.
- **`formshare/tests/test_18_actions_editor.py`** runs the shipped bundle in
  Node, and is skipped without `node`. Every golden program but
  `failure_no_property`, and every module the compiler writes, must come out
  of the checks clean. It also tests `catalogue_for_editor` without a
  database.
- **The case journey** (`tests/steps/case_journey.py`) checks the pages:
  - the bundle and the names on the code page, and neither on the list;
  - the phrases with `{name}`;
  - code posted with CR LF stored with LF.

## Things to know

- **Compare Lezer nodes by position.** A node is made afresh on each access,
  so `===` between two of them is false.
- **JavaScript's grammar names an assignment `AssignmentExpression`.**
- **A check mirrors the server or the prelude, word for word where it can.**
  A change to `load_module`, the prelude (RSTools'
  `kotlinrstools/actions/prelude.js`) or the server's writes changes
  `src/lint.js` too.
- **The language level is not checked.** The interim engine is ES2020, and
  the dry run reports a module that reaches further.
- **Size.** The bundle is 532 KB minified, 182 KB gzipped. Only the code and
  test pages of an action load it.
- **A theme added before another overrides it.** CodeMirror gives an earlier
  extension the higher precedence, styles included: `minHeight` is placed
  before `actionsTheme`.
