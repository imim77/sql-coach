import type { ExerciseDetail, ExerciseSummary, HintResponse, QueryResult } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new Error("Can't reach the coach service. Start the backend on port 8000.");
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    return `Request failed (${response.status}).`;
  }
  return `Request failed (${response.status}).`;
}

export function fetchExercises(): Promise<ExerciseSummary[]> {
  return request("/api/exercises");
}

export function fetchExercise(id: string): Promise<ExerciseDetail> {
  return request(`/api/exercises/${id}`);
}

export function runQuery(id: string, sql: string): Promise<QueryResult> {
  return request(`/api/exercises/${id}/run`, {
    method: "POST",
    body: JSON.stringify({ sql }),
  });
}

export function checkAnswer(id: string, sql: string): Promise<QueryResult> {
  return request(`/api/exercises/${id}/check`, {
    method: "POST",
    body: JSON.stringify({ sql }),
  });
}

export function fetchHint(id: string, sql: string, level: number): Promise<HintResponse> {
  return request(`/api/exercises/${id}/hint`, {
    method: "POST",
    body: JSON.stringify({ sql, level }),
  });
}

export function fetchSolution(id: string): Promise<{ reference_sql: string }> {
  return request(`/api/exercises/${id}/solution`, { method: "POST" });
}

export function continueExercises(afterId: string): Promise<ExerciseSummary[]> {
  return request("/api/exercises/continue", {
    method: "POST",
    body: JSON.stringify({ after_id: afterId }),
  });
}
