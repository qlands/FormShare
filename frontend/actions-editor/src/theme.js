// The editor's chrome, in the page's own colours (Inspinia: #e5e6e7 borders,
// #1ab394 for focus), with the font the textarea had.

import {EditorView} from "@codemirror/view";

export const actionsTheme = EditorView.theme({
  "&": {
    border: "1px solid #e5e6e7",
    borderRadius: "1px",
    backgroundColor: "#ffffff",
    fontSize: "12px",
    maxHeight: "70vh",
  },
  "&.cm-focused": {outline: "none", borderColor: "#1ab394"},
  ".cm-scroller": {
    fontFamily: "SFMono-Regular, Menlo, Consolas, \"Liberation Mono\", monospace",
    lineHeight: "1.55",
    overflow: "auto",
  },
  ".cm-content, .cm-gutter": {minHeight: "380px"},
  ".cm-gutters": {backgroundColor: "#f8f9fa", color: "#999999", borderRight: "1px solid #e5e6e7"},
  ".cm-activeLine": {backgroundColor: "#f3faf8"},
  ".cm-activeLineGutter": {backgroundColor: "#e7f5f1"},
  ".cm-placeholder": {color: "#aaaaaa"},
  // Above the page's fixed navigation and its dialogs (2050).
  ".cm-tooltip": {zIndex: "2100", fontSize: "12px"},
  ".cm-tooltip.cm-tooltip-autocomplete > ul": {
    fontFamily: "SFMono-Regular, Menlo, Consolas, \"Liberation Mono\", monospace",
    maxHeight: "18em",
  },
  ".cm-tooltip-autocomplete ul li[aria-selected]": {backgroundColor: "#1ab394", color: "#ffffff"},
  ".cm-tooltip-autocomplete ul li[aria-selected] .cm-completionDetail": {color: "#e8f7f3"},
  ".cm-completionDetail": {marginLeft: "1.2em", color: "#888888", fontStyle: "normal"},
  ".cm-completionInfo": {maxWidth: "380px", padding: "6px 9px", lineHeight: "1.45"},
  ".cm-tooltip-autocomplete completion-section": {
    fontFamily: "\"open sans\", \"Helvetica Neue\", Helvetica, Arial, sans-serif",
    color: "#676a6c",
    borderBottom: "1px solid #e5e6e7",
    padding: "2px 6px",
  },
  ".cm-actions-signature": {padding: "4px 8px", maxWidth: "520px", backgroundColor: "#ffffff"},
  ".cm-actions-signature code": {color: "#333333", backgroundColor: "transparent", padding: "0", fontSize: "12px"},
  ".cm-actions-signature b": {color: "#1ab394"},
  ".cm-actions-signature-doc": {color: "#676a6c", marginTop: "2px", whiteSpace: "normal"},
  ".cm-diagnostic": {padding: "4px 8px", maxWidth: "520px", whiteSpace: "normal"},
  ".cm-actions-failed": {backgroundColor: "#fdecea"},
  ".cm-actions-failed.cm-activeLine": {backgroundColor: "#fbdcd8"},
});
