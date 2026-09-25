import type { QueryResult } from "../types";

function formatCell(value: unknown): { text: string; muted: boolean } {
  if (value === null || value === undefined) return { text: "null", muted: true };
  if (typeof value === "boolean") return { text: value ? "true" : "false", muted: false };
  return { text: String(value), muted: false };
}

function rowLabel(count: number): string {
  return count === 1 ? "1 row" : `${count} rows`;
}

function Verdict({ correct }: { correct: boolean }) {
  const label = correct ? "Correct" : "Incorrect";
  return (
    <div
      className={`flex h-32 w-32 shrink-0 items-center justify-center rounded-full motion-safe:animate-pop ${
        correct ? "bg-kelp text-manifest" : "bg-manifest text-rust"
      }`}
      role="img"
      aria-label={label}
    >
      {correct ? (
        <svg viewBox="0 0 24 24" className="h-20 w-20" fill="none" aria-hidden="true">
          <path
            d="M5 13l4 4L19 7"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-20 w-20" fill="none" aria-hidden="true">
          <path
            d="M6 6l12 12M18 6L6 18"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>
      )}
    </div>
  );
}

export default function ResultPane({ result }: { result: QueryResult | null }) {
  const correct = result?.error == null && result?.correct === true;
  const wrong = result?.error == null && result?.correct === false;
  const frame = correct ? "border-kelp" : wrong || result?.error ? "border-2 border-rust" : "border-lead";

  return (
    <section
      aria-live="polite"
      className={`min-h-48 min-w-0 overflow-auto border bg-manifest lg:col-span-8 ${frame}`}
    >
      {result?.error ? (
        <div className="border-b border-rust bg-rust/10 px-4 py-3">
          <p className="text-lg font-semibold text-rust">Postgres rejected the query.</p>
          <p className="mt-1 font-mono text-sm">{result.error}</p>
        </div>
      ) : null}
      {correct ? (
        <div className="flex flex-wrap items-center gap-4 border-b border-kelp bg-kelp/15 px-4 py-4">
          <Verdict correct />
          <p className="font-display text-3xl tracking-tight text-kelp">That result matches.</p>
        </div>
      ) : null}
      {wrong ? (
        <div className="flex flex-wrap items-center gap-4 border-b border-rust bg-rust px-4 py-4 text-manifest">
          <Verdict correct={false} />
          <div>
            <p className="font-display text-3xl tracking-tight">Result does not match.</p>
            <p className="mt-1 text-base">
              {rowLabel(result?.row_count ?? 0)} returned, {rowLabel(result?.expected_row_count ?? 0)}{" "}
              expected. {result?.detail}
            </p>
          </div>
        </div>
      ) : null}
      {!result ? (
        <p className="px-3 py-4 text-sm text-fathom/70">Run the query to see rows here.</p>
      ) : null}
      {result && result.error === null && result.columns ? (
        result.rows && result.rows.length > 0 ? (
          <table className="w-full border-collapse text-left font-mono text-sm motion-safe:animate-rise">
            <thead>
              <tr className="border-b border-lead">
                {result.columns.map((column) => (
                  <th key={column} className="px-3 py-2 text-xs font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b border-lead/70">
                  {row.map((cell, cellIndex) => {
                    const formatted = formatCell(cell);
                    return (
                      <td
                        key={cellIndex}
                        className={`px-3 py-1.5 ${formatted.muted ? "text-fathom/40 italic" : ""}`}
                      >
                        {formatted.text}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="px-3 py-4 font-mono text-sm">No rows.</p>
        )
      ) : null}
    </section>
  );
}
