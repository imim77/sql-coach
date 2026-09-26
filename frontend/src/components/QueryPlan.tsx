import { useEffect, useId, useRef, useState } from "react";
import mermaid from "mermaid";

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

export default function QueryPlan({ mermaidSource }: { mermaidSource: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const renderSeq = useRef(0);
  const instanceId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [failed, setFailed] = useState(false);
  const hasSource = mermaidSource.length > 0;

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
