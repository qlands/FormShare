# actions_editor.min.js

The code editor of a form's case actions in expert mode, built from
`frontend/actions-editor` (its README) with `npm run build`. Do not edit this
file: change `src/` there, rebuild, and commit both.

- CodeMirror 6: `@codemirror/view` 6.43.14, `state` 6.7.6, `language` 6.13.1,
  `autocomplete` 6.20.3, `commands` 6.11.1, `lint` 6.9.7, `search` 6.7.2,
  `lang-javascript` 6.2.5 (`@lezer/javascript` 1.5.6).
- esbuild 0.28.2: `--bundle --format=iife --minify --target=es2020`.
- `THIRD_PARTY_LICENSES.txt`: every bundled package and its licence, all MIT.
- First built 2026-10-19: 532 KB, 182 KB gzipped.
