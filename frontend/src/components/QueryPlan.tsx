import { useEffect, useId, useRef, useState } from "react";
import mermaid from "mermaid";
import { Button } from "@/components/ui/button";

let mermaidReady = false;

function ensureMermaid() {
  if (mermaidReady) {
    return;
  }
  // Mermaid 12 applies root htmlLabels before flowchart.htmlLabels. SVG labels
  // still split on <br/>, so line breaks in node text stay visible.
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    htmlLabels: false,
    suppressErrorRendering: true,
    flowchart: { htmlLabels: false },
  });
  mermaidReady = true;
}

export type PlanFrame = {
  op: string;
  label: string;
  detail: string;
  row_count?: number | null;
  dropped?: number | null;
  columns?: string[] | null;
  rows?: unknown[][] | null;
};

function isJoinFrame(frame: PlanFrame): boolean {
  return frame.op === "join" || frame.label.toUpperCase().endsWith("JOIN");
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function FrameTable({ frame }: { frame: PlanFrame }) {
  const columns = frame.columns ?? [];
  const rows = frame.rows ?? [];
  if (columns.length === 0 && rows.length === 0) {
    return null;
  }

  return (
    <div className="min-w-0 overflow-x-auto rounded-md border border-border bg-card">
      <table className="w-full border-collapse text-left text-sm">
        {columns.length > 0 ? (
          <thead>
            <tr className="border-b border-border">
              {columns.map((column, columnIndex) => (
                <th
                  key={`${column}-${columnIndex}`}
                  className="px-2 py-1 font-medium text-muted-foreground"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-border last:border-b-0">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-2 py-1 font-mono">
                  {formatCell(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlanPlayer({ frames }: { frames: PlanFrame[] }) {
  const [run, setRun] = useState(0);
  const [trackedFrames, setTrackedFrames] = useState(frames);
  const [trackedRun, setTrackedRun] = useState(run);
  const [index, setIndex] = useState(0);
  const [tableIndex, setTableIndex] = useState(0);
  const [tableVisible, setTableVisible] = useState(true);
  const fadeTimer = useRef<number | null>(null);
  const lastIndex = frames.length - 1;

  if (trackedFrames !== frames || trackedRun !== run) {
    setTrackedFrames(frames);
    setTrackedRun(run);
    setIndex(0);
    setTableIndex(0);
    setTableVisible(true);
  }

  const frame = frames[Math.min(index, lastIndex)] ?? frames[0];
  const tableFrame = frames[Math.min(tableIndex, lastIndex)] ?? frames[0];
  const dropped = frame.dropped;

  useEffect(() => {
    if (fadeTimer.current != null) {
      window.clearTimeout(fadeTimer.current);
      fadeTimer.current = null;
    }
  }, [frames, run]);

  useEffect(() => {
    if (index >= lastIndex) {
      return;
    }
    const timer = window.setTimeout(() => {
      setIndex((current) => Math.min(current + 1, lastIndex));
    }, 900);
    return () => window.clearTimeout(timer);
  }, [index, lastIndex, run]);

  useEffect(() => {
    if (index === tableIndex) {
      setTableVisible(true);
      return;
    }
    if (fadeTimer.current != null) {
      window.clearTimeout(fadeTimer.current);
      fadeTimer.current = null;
    }
    setTableVisible(false);
    fadeTimer.current = window.setTimeout(() => {
      fadeTimer.current = null;
      setTableIndex(index);
      setTableVisible(true);
    }, 300);
    return () => {
      if (fadeTimer.current != null) {
        window.clearTimeout(fadeTimer.current);
        fadeTimer.current = null;
      }
    };
  }, [index, tableIndex]);

  return (
    <div className="flex min-w-0 flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          {isJoinFrame(frame) ? (
            <p className="w-fit rounded-md border border-border bg-card px-2 py-0.5 text-sm font-medium">
              {frame.label}
            </p>
          ) : (
            <p className="text-sm font-medium">{frame.label}</p>
          )}
          <p className="text-sm text-muted-foreground">{frame.detail}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setRun((current) => current + 1)}>
          Replay
        </Button>
      </div>
      {typeof frame.row_count === "number" ? (
        <p className="text-sm text-muted-foreground">{frame.row_count} rows</p>
      ) : null}
      {typeof dropped === "number" && dropped > 0 ? (
        <p key={`${run}-${index}`} className="text-sm text-destructive animate-pulse">
          {dropped} rows dropped
        </p>
      ) : null}
      <div className={`transition-opacity duration-300 ${tableVisible ? "opacity-100" : "opacity-0"}`}>
        <FrameTable frame={tableFrame} />
      </div>
    </div>
  );
}

export default function QueryPlan({
  mermaidSource,
  frames,
}: {
  mermaidSource: string;
  frames?: PlanFrame[];
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const renderSeq = useRef(0);
  const instanceId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [failed, setFailed] = useState(false);
  const hasSource = mermaidSource.length > 0;
  const hasFrames = frames != null && frames.length > 0;

  useEffect(() => {
    if (!hasSource) {
      setFailed(false);
      return;
    }

    const host = hostRef.current;
    if (!host) {
      return;
    }

    let cancelled = false;
    setFailed(false);
    host.replaceChildren();
    const id = `queryplan${instanceId}${++renderSeq.current}`;

    try {
      ensureMermaid();
      void mermaid.render(id, mermaidSource).then(
        ({ svg }) => {
          if (cancelled) {
            return;
          }
          host.innerHTML = svg;
        },
        () => {
          if (cancelled) {
            return;
          }
          host.replaceChildren();
          setFailed(true);
        },
      );
    } catch {
      if (!cancelled) {
        host.replaceChildren();
        setFailed(true);
      }
    }

    return () => {
      cancelled = true;
    };
  }, [hasSource, instanceId, mermaidSource]);

  return (
    <section className="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-medium text-foreground">How this query runs</h2>
        <p className="text-sm text-muted-foreground">
          Each step is what that clause does to the rows.
        </p>
      </div>
      {hasFrames ? <PlanPlayer frames={frames} /> : null}
      {hasSource ? (
        <div className="min-w-0 overflow-auto font-mono">
          {failed ? (
            <p className="font-mono text-sm text-muted-foreground">
              The diagram could not be drawn.
            </p>
          ) : null}
          <div ref={hostRef} className={failed ? "hidden" : "min-w-0"} />
        </div>
      ) : null}
    </section>
  );
}
