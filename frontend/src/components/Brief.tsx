import type { ExerciseDetail } from "../types";

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export default function Brief({ exercise }: { exercise: ExerciseDetail | null }) {
  if (!exercise) {
    return (
      <section className="min-w-0 border border-lead bg-manifest p-4 text-sm lg:col-span-4 lg:overflow-auto">
        Loading the exercise…
      </section>
    );
  }

  return (
    <section className="max-h-96 min-w-0 overflow-auto border border-lead bg-manifest p-4 lg:col-span-4 lg:max-h-none">
      <h1 className="font-display text-2xl tracking-tight text-sounding">{exercise.title}</h1>
      <p className="mt-1 font-mono text-xs uppercase tracking-wide text-sounding">{exercise.dataset}</p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {exercise.concepts.map((concept) => (
          <li
            key={concept}
            className="bg-wash px-2 py-0.5 font-mono text-xs uppercase tracking-wide text-sounding"
          >
            {concept}
          </li>
        ))}
      </ul>
      <p className="mt-4 whitespace-pre-wrap text-[15px] leading-relaxed">{exercise.prompt}</p>
      <h2 className="mt-6 font-mono text-xs uppercase tracking-wide text-sounding">Tables</h2>
      <div className="mt-2">
        {exercise.schema.map((table) => (
          <details key={table.name} className="border-t border-lead py-2">
            <summary className="cursor-pointer font-mono text-sm">{table.name}</summary>
            <p className="mt-2 font-mono text-xs leading-5 text-fathom/80">
              {table.columns
                .map((column) => `${column.name} ${column.data_type}${column.nullable ? " null" : ""}`)
                .join(", ")}
            </p>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full border-collapse text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-lead">
                    {table.sample_columns.map((column) => (
                      <th key={column} className="px-2 py-1 font-medium">
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.sample_rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-b border-lead/70">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-2 py-1">
                          {formatCell(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
