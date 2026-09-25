import { useCallback, useEffect, useRef, useState } from "react";
import {
  checkAnswer,
  continueExercises,
  fetchExercise,
  fetchExercises,
  fetchHint,
  fetchSolution,
  runQuery,
} from "./api";
import Brief from "./components/Brief";
import CoachSlip from "./components/CoachSlip";
import Header from "./components/Header";
import ResultPane from "./components/ResultPane";
import SqlEditor from "./components/SqlEditor";
import type { ExerciseDetail, ExerciseSummary, HintResponse, QueryResult } from "./types";

const PASSED_KEY = "sql-coach-passed";

const primary =
  "bg-sounding px-3 py-1.5 text-sm font-semibold text-manifest hover:bg-sounding/90 disabled:opacity-50";
const quiet =
  "border border-lead bg-manifest px-3 py-1.5 text-sm hover:bg-wash disabled:opacity-50";

function loadPassed(): Set<string> {
  try {
    const raw = sessionStorage.getItem(PASSED_KEY);
    const ids = raw ? (JSON.parse(raw) as unknown) : [];
    if (!Array.isArray(ids)) return new Set();
    return new Set(ids.filter((id): id is string => typeof id === "string"));
  } catch {
    return new Set();
  }
}

export default function App() {
  const [exercises, setExercises] = useState<ExerciseSummary[]>([]);
  const [index, setIndex] = useState(0);
  const [detail, setDetail] = useState<ExerciseDetail | null>(null);
  const [sql, setSql] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [hint, setHint] = useState<HintResponse | null>(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [solution, setSolution] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [passed, setPassed] = useState<Set<string>>(loadPassed);
  const [generating, setGenerating] = useState(false);
  const requested = useRef<Set<string>>(new Set());

  useEffect(() => {
    fetchExercises()
      .then(setExercises)
      .catch((error: unknown) => setPageError(messageOf(error)));
  }, []);

  const exerciseId = exercises[index]?.id;

  useEffect(() => {
    if (!exerciseId) return;
    let cancelled = false;
    setDetail(null);
    setSql("");
    setResult(null);
    setHint(null);
    setHintLevel(0);
    setSolution(null);
    fetchExercise(exerciseId)
      .then((exercise) => {
        if (!cancelled) {
          setDetail(exercise);
          setPageError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setPageError(messageOf(error));
      });
    return () => {
      cancelled = true;
    };
  }, [exerciseId]);

  const unlockedThrough = exercises.findIndex((exercise) => !passed.has(exercise.id));
  const openThrough = unlockedThrough === -1 ? Math.max(exercises.length - 1, 0) : unlockedThrough;

  function markPassed(id: string) {
    setPassed((current) => {
      if (current.has(id)) return current;
      const next = new Set(current);
      next.add(id);
      sessionStorage.setItem(PASSED_KEY, JSON.stringify([...next]));
      return next;
    });
  }

  function applyResult(next: QueryResult) {
    setResult(next);
    if (exerciseId && next.error == null && next.correct === true) markPassed(exerciseId);
  }

  function goTo(next: number) {
    if (next < 0 || next > openThrough) return;
    setIndex(next);
  }

  const lastId = exercises[exercises.length - 1]?.id;
  const canContinue = Boolean(lastId && passed.has(lastId));

  const requestNext = useCallback(async (afterId: string) => {
    if (requested.current.has(afterId)) return;
    requested.current.add(afterId);
    setGenerating(true);
    setPageError(null);
    try {
      setExercises(await continueExercises(afterId));
    } catch (error: unknown) {
      requested.current.delete(afterId);
      setPageError(messageOf(error));
    } finally {
      setGenerating(false);
    }
  }, []);

  useEffect(() => {
    if (lastId && passed.has(lastId)) void requestNext(lastId);
  }, [lastId, passed, requestNext]);

  const onRun = useCallback(async () => {
    if (!exerciseId || !sql.trim() || busy) return;
    setBusy(true);
    try {
      applyResult(await runQuery(exerciseId, sql));
    } catch (error: unknown) {
      setResult({ columns: null, rows: null, error: messageOf(error) });
    } finally {
      setBusy(false);
    }
  }, [busy, exerciseId, sql]);

  async function onCheck() {
    if (!exerciseId || !sql.trim() || busy) return;
    setBusy(true);
    try {
      applyResult(await checkAnswer(exerciseId, sql));
    } catch (error: unknown) {
      setResult({ columns: null, rows: null, error: messageOf(error) });
    } finally {
      setBusy(false);
    }
  }

  async function onHint() {
    if (!exerciseId || !sql.trim() || busy) return;
    const level = Math.min(hintLevel + 1, 3);
    setBusy(true);
    try {
      const response = await fetchHint(exerciseId, sql, level);
      setHint(response);
      setHintLevel(level);
      applyResult(response);
    } catch (error: unknown) {
      setResult({ columns: null, rows: null, error: messageOf(error) });
    } finally {
      setBusy(false);
    }
  }

  async function onSolution() {
    if (!exerciseId || busy) return;
    setBusy(true);
    try {
      const response = await fetchSolution(exerciseId);
      setSolution(response.reference_sql);
    } catch (error: unknown) {
      setPageError(messageOf(error));
    } finally {
      setBusy(false);
    }
  }

  if (pageError && exercises.length === 0) {
    return (
      <main className="mx-auto max-w-lg px-6 py-16">
        <h1 className="font-display text-3xl text-sounding">SQL Coach</h1>
        <p className="mt-4 text-sm leading-relaxed">{pageError}</p>
      </main>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-wash text-fathom lg:h-screen lg:overflow-hidden">
      <Header
        exercises={exercises}
        index={index}
        unlockedThrough={openThrough}
        generating={generating}
        canContinue={
          canContinue && !generating && index === exercises.length - 1
        }
        onContinue={() => {
          if (lastId) void requestNext(lastId);
        }}
        onIndex={goTo}
      />
      {pageError ? (
        <p className="bg-rust px-4 py-2 text-sm text-manifest">{pageError}</p>
      ) : null}
      <main className="grid min-w-0 flex-1 gap-3 p-3 lg:min-h-0 lg:grid-cols-12 lg:grid-rows-[minmax(0,1.2fr)_minmax(14rem,0.9fr)]">
        <Brief exercise={detail} />
        <section className="flex min-h-80 min-w-0 flex-col border border-lead bg-manifest lg:col-span-8 lg:min-h-0">
          <div className="min-h-64 flex-1">
            {exerciseId ? (
              <SqlEditor exerciseId={exerciseId} sql={sql} onChange={setSql} onRun={onRun} />
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-lead px-3 py-2">
            <button type="button" className={primary} disabled={busy || !sql.trim()} onClick={onRun}>
              Run
            </button>
            <button type="button" className={quiet} disabled={busy || !sql.trim()} onClick={onCheck}>
              Check answer
            </button>
            <span className="ml-auto text-xs text-fathom/60">Ctrl/Cmd + Enter runs</span>
          </div>
        </section>
        <ResultPane result={result} />
        <CoachSlip
          hint={hint}
          solution={solution}
          busy={busy}
          canHint={sql.trim().length > 0}
          onHint={onHint}
          onSolution={onSolution}
        />
      </main>
    </div>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
