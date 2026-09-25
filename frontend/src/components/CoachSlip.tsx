import type { HintResponse } from "../types";

type CoachSlipProps = {
  hint: HintResponse | null;
  solution: string | null;
  busy: boolean;
  canHint: boolean;
  onHint: () => void;
  onSolution: () => void;
};

export default function CoachSlip({
  hint,
  solution,
  busy,
  canHint,
  onHint,
  onSolution,
}: CoachSlipProps) {
  return (
    <aside className="flex min-w-0 flex-col gap-4 border border-lead bg-manifest p-4 lg:col-span-4 lg:overflow-auto">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-mono text-xs uppercase tracking-wide text-sounding">Coach</h2>
        <button
          type="button"
          className="border border-lead bg-manifest px-3 py-1.5 text-sm hover:bg-wash disabled:opacity-50"
          disabled={!canHint || busy}
          onClick={onHint}
        >
          Hint
        </button>
      </div>
      {hint ? (
        <div className="border-l-4 border-l-buoy bg-wash px-3 py-3">
          <p className="font-mono text-xs uppercase tracking-wide text-buoy">
            {hint.source === "coach" ? "Coach" : "Saved note"} · Note {hint.level} of 3
          </p>
          <p className="mt-2 text-sm leading-relaxed">{hint.note}</p>
        </div>
      ) : (
        <p className="text-sm leading-relaxed text-fathom/75">
          A miss can take a note. Hints stop short of the query.
        </p>
      )}
      {solution ? (
        <div>
          <p className="font-mono text-xs uppercase tracking-wide text-sounding">Solution</p>
          <pre className="mt-2 overflow-auto border border-lead bg-wash p-3 font-mono text-xs leading-5">
            {solution}
          </pre>
        </div>
      ) : (
        <button
          type="button"
          className="self-start text-sm text-fathom/70 underline-offset-2 hover:underline disabled:opacity-50"
          disabled={busy}
          onClick={onSolution}
        >
          Show solution
        </button>
      )}
    </aside>
  );
}
