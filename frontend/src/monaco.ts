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
    "editor.background": "#fafaf7",
    "editor.foreground": "#26251e",
    "editorLineNumber.foreground": "#a09c92",
    "editor.selectionBackground": "#e6e5e0",
    "editorCursor.foreground": "#f54e00",
  },
});
