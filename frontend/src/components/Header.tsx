import type { ExerciseSummary } from "../types";

type HeaderProps = {
  exercises: ExerciseSummary[];
  index: number;
  unlockedThrough: number;
  generating: boolean;
  canContinue: boolean;
  onContinue: () => void;
  onIndex: (index: number) => void;
};

const headerControl =
  "border border-manifest/30 px-2 py-1 text-sm text-manifest hover:bg-manifest/10 disabled:opacity-40 focus-visible:ring-manifest focus-visible:ring-offset-sounding";

export default function Header({
  exercises,
  index,
  unlockedThrough,
  generating,
  canContinue,
  onContinue,
  onIndex,
}: HeaderProps) {
  const current = exercises[index];
  const position = exercises.length === 0 ? "0 of 0" : `${index + 1} of ${exercises.length}`;
  const nextLocked = index < exercises.length - 1 && index >= unlockedThrough;

  return (
    <header className="flex w-full shrink-0 flex-wrap items-center justify-between gap-3 bg-sounding px-4 py-3 text-manifest">
      <p className="font-display text-xl tracking-tight">SQL Coach</p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={headerControl}
          aria-label="Previous exercise"
          disabled={index <= 0}
          onClick={() => onIndex(index - 1)}
        >
          ‹
        </button>
        <span className="min-w-14 text-center font-mono text-sm">{position}</span>
        <button
          type="button"
          className={headerControl}
          aria-label="Next exercise"
          title={nextLocked ? "Pass this exercise to open the next one." : undefined}
          disabled={generating || nextLocked || index >= exercises.length - 1}
          onClick={() => onIndex(index + 1)}
        >
          ›
        </button>
        <select
          aria-label="Exercise"
          className="max-w-[42vw] bg-sounding px-1 py-1 text-sm text-manifest focus-visible:ring-manifest focus-visible:ring-offset-sounding sm:max-w-52"
          value={current?.id ?? ""}
          onChange={(event) => {
            const next = exercises.findIndex((item) => item.id === event.target.value);
            if (next >= 0) onIndex(next);
          }}
        >
          {exercises.map((exercise, optionIndex) => (
            <option key={exercise.id} value={exercise.id} disabled={optionIndex > unlockedThrough}>
              {exercise.title}
            </option>
          ))}
        </select>
      </div>
      {generating ? (
        <p className="text-sm text-manifest/90">Writing the next exercise…</p>
      ) : canContinue ? (
        <button
          type="button"
          className="text-sm text-manifest underline-offset-2 hover:underline"
          onClick={onContinue}
        >
          Write the next exercise
        </button>
      ) : nextLocked ? (
        <p className="text-sm text-manifest/90">Pass this exercise to open the next one.</p>
      ) : (
        <p className="hidden text-sm tracking-wide sm:block">{current?.dataset ?? "Northline"}</p>
      )}
    </header>
  );
}
