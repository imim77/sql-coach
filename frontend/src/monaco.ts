import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import "monaco-editor/esm/vs/basic-languages/sql/sql.contribution";

self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker();
  },
};

loader.config({ monaco });

monaco.editor.defineTheme("northline", {
  base: "vs",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#F7FBFC",
    "editor.foreground": "#0E2A33",
    "editorLineNumber.foreground": "#8AA0A8",
    "editor.selectionBackground": "#D3E4EA",
    "editorCursor.foreground": "#163A4A",
  },
});
