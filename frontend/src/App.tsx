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
import ExerciseSidebar from "./components/ExerciseSidebar";
import Header from "./components/Header";
import ResultPane from "./components/ResultPane";
import SqlEditor from "./components/SqlEditor";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import type { ExerciseDetail, ExerciseSummary, HintResponse, QueryResult } from "./types";

const PASSED_KEY = "sql-coach-passed";

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
  const [listReady, setListReady] = useState(false);
  const [passed, setPassed] = useState<Set<string>>(loadPassed);
  const [generating, setGenerating] = useState(false);
  const requested = useRef<Set<string>>(new Set());

  useEffect(() => {
    fetchExercises()
      .then(setExercises)
      .catch((error: unknown) => setPageError(messageOf(error)))
      .finally(() => setListReady(true));
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
      <main className="mx-auto flex max-w-lg flex-col gap-4 px-6 py-16">
        <h1 className="font-display text-3xl">SQL Coach</h1>
        <p className="text-sm leading-relaxed">{pageError}</p>
      </main>
    );
  }

  const current = exercises[index];

  return (
    <SidebarProvider className="h-svh overflow-hidden">
        <ExerciseSidebar
          exercises={exercises}
          index={index}
          openThrough={openThrough}
          passed={passed}
          loading={!listReady}
          generating={generating}
          canContinue={canContinue && !generating && index === exercises.length - 1}
          onContinue={() => {
            if (lastId) void requestNext(lastId);
          }}
          onIndex={goTo}
        />
        <SidebarInset className="min-h-0 overflow-hidden">
          <Header title={current?.title ?? ""} dataset={current?.dataset ?? "Northline"} />
          <Separator />
          {pageError ? (
            <div className="shrink-0 px-3 pt-3">
              <Alert variant="destructive">
                <AlertDescription>{pageError}</AlertDescription>
              </Alert>
            </div>
          ) : null}
          <div className="flex min-h-0 flex-1 flex-col overflow-auto lg:flex-row lg:overflow-hidden">
            <section className="flex min-h-0 min-w-0 flex-col border-b lg:w-1/2 lg:border-r lg:border-b-0">
              <div className="min-h-0 flex-1 overflow-auto px-4 py-4">
                <Brief exercise={detail} />
              </div>
              <Separator />
              <div className="max-h-64 shrink-0 overflow-auto">
                <CoachSlip
                  hint={hint}
                  solution={solution}
                  busy={busy}
                  canHint={sql.trim().length > 0}
                  onHint={onHint}
                />
              </div>
            </section>
            <section className="flex min-h-[28rem] min-w-0 flex-1 flex-col lg:min-h-0">
              <div className="min-h-48 flex-1">
                {exerciseId ? (
                  <SqlEditor exerciseId={exerciseId} sql={sql} onChange={setSql} onRun={onRun} />
                ) : null}
              </div>
              <div className="max-h-[40%] min-h-32 shrink-0 overflow-auto border-t">
                <ResultPane result={result} />
              </div>
              <Separator />
              <div className="flex shrink-0 flex-wrap items-center gap-2 px-3 py-2">
                <Button type="button" disabled={busy || !sql.trim()} onClick={onRun}>
                  Run
                </Button>
                <Button type="button" variant="outline" disabled={busy || !sql.trim()} onClick={onCheck}>
                  Check answer
                </Button>
                <span className="ml-auto text-xs text-muted-foreground">Ctrl/Cmd + Enter runs</span>
              </div>
            </section>
          </div>
        </SidebarInset>
      </SidebarProvider>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
