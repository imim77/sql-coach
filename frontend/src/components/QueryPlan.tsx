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
  selected_columns?: string[] | null;
  rows?: unknown[][] | null;
};

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

function columnSelected(header: string, selected: string[]) {
  const name = header.toLowerCase();
  const bare = name.slice(name.lastIndexOf(".") + 1);
  return selected.some((item) => {
    const wanted = item.toLowerCase();
    const wantedBare = wanted.slice(wanted.lastIndexOf(".") + 1);
    return wanted === name || wantedBare === name || wanted === bare;
  });
}

function FrameTable({
  frame,
  leaving = false,
  selected = [],
}: {
  frame: PlanFrame;
  leaving?: boolean;
  selected?: string[];
}) {
  const columns = frame.columns ?? [];
  const rows = frame.rows ?? [];
  if (columns.length === 0 && rows.length === 0) {
    return null;
  }
  const picked = columns.map((column) => columnSelected(column, selected));

  return (
    <div className="min-w-0 overflow-x-auto rounded-md border border-border bg-card">
      <table className="w-full border-collapse text-left text-sm">
        {columns.length > 0 ? (
          <thead>
            <tr className="border-b border-border">
              {columns.map((column, columnIndex) => (
                <th
                  key={`${column}-${columnIndex}`}
                  className={`px-3 py-2 font-medium transition-colors duration-700 ${
                    picked[columnIndex]
                      ? "bg-primary/15 text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={`border-b border-border transition-opacity duration-1000 last:border-b-0 ${
                leaving ? "text-muted-foreground line-through opacity-50" : "opacity-100"
              }`}
            >
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className={`px-3 py-2 font-mono transition-colors duration-700 ${
                    picked[cellIndex] ? "bg-primary/15 text-foreground" : ""
                  }`}
                >
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

const ROW_LEAVE_MS = 1400;

function PlanPlayer({ frames }: { frames: PlanFrame[] }) {
  const [run, setRun] = useState(0);
  const [trackedFrames, setTrackedFrames] = useState(frames);
  const [trackedRun, setTrackedRun] = useState(run);
  const [index, setIndex] = useState(0);
  const [shownIndex, setShownIndex] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const lastIndex = frames.length - 1;

  if (trackedFrames !== frames || trackedRun !== run) {
    setTrackedFrames(frames);
    setTrackedRun(run);
    setIndex(0);
    setShownIndex(0);
    setLeaving(false);
  }

  const frame = frames[Math.min(index, lastIndex)] ?? frames[0];
  const shown = frames[Math.min(shownIndex, lastIndex)] ?? frames[0];
  const dropped = frame.dropped;
  const dropping = typeof dropped === "number" && dropped > 0;
  const selected =
    [...frames].reverse().find((item) => (item.selected_columns?.length ?? 0) > 0)?.selected_columns ??
    [];

  useEffect(() => {
    if (index === shownIndex) {
      setLeaving(false);
      return;
    }
    if (!dropping) {
      setShownIndex(index);
      setLeaving(false);
      return;
    }
    setLeaving(true);
    const timer = window.setTimeout(() => {
      setShownIndex(index);
      setLeaving(false);
    }, ROW_LEAVE_MS);
    return () => window.clearTimeout(timer);
  }, [dropping, index, shownIndex]);

  return (
    <div className="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-card p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Step {index + 1} of {frames.length}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {frames.map((item, itemIndex) => (
              <button
                key={`${item.op}-${itemIndex}`}
                type="button"
                onClick={() => setIndex(itemIndex)}
                className={`cursor-pointer rounded-md border bg-transparent px-2 py-0.5 text-xs transition-colors duration-700 ${
                  itemIndex === index
                    ? "border-foreground text-foreground"
                    : itemIndex < index
                      ? "border-border text-muted-foreground"
                      : "border-transparent text-muted-foreground/60"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{frame.detail}</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={index === 0}
          onClick={() => setIndex((current) => Math.max(current - 1, 0))}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={index >= lastIndex}
          onClick={() => setIndex((current) => Math.min(current + 1, lastIndex))}
        >
          Next
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => setRun((current) => current + 1)}>
          Replay
        </Button>
      </div>
      <div className="flex flex-wrap items-baseline gap-3">
        {typeof frame.row_count === "number" ? (
          <p className="text-sm text-muted-foreground">
            {leaving && typeof shown.row_count === "number" ? shown.row_count : frame.row_count} rows
          </p>
        ) : null}
        {dropping ? (
          <p className="text-sm text-destructive transition-opacity duration-700">
            {dropped} {dropped === 1 ? "row leaves" : "rows leave"}
          </p>
        ) : null}
      </div>
      <div className={`transition-opacity duration-700 ${leaving ? "opacity-40" : "opacity-100"}`}>
        <FrameTable frame={shown} leaving={leaving} selected={selected} />
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
