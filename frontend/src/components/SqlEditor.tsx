import Editor, { type OnMount } from "@monaco-editor/react";
import { useRef } from "react";

type SqlEditorProps = {
  exerciseId: string;
  sql: string;
  onChange: (sql: string) => void;
  onRun: () => void;
};

export default function SqlEditor({ exerciseId, sql, onChange, onRun }: SqlEditorProps) {
  const onRunRef = useRef(onRun);
  onRunRef.current = onRun;

  const handleMount: OnMount = (editor, monaco) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onRunRef.current();
    });
  };

  return (
    <Editor
      key={exerciseId}
      height="100%"
      language="sql"
      theme="northline"
      value={sql}
      onChange={(value) => onChange(value ?? "")}
      onMount={handleMount}
      options={{
        minimap: { enabled: false },
        fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
        fontSize: 14,
        wordWrap: "on",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        padding: { top: 12, bottom: 12 },
        overviewRulerLanes: 0,
        renderLineHighlight: "line",
        tabSize: 2,
      }}
    />
  );
}
