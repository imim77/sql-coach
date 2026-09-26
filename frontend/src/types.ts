export type ExerciseSummary = {
  id: string;
  title: string;
  concepts: string[];
  dataset: string;
  tables?: string[];
};

export type CreateTaskRequest = {
  id: string;
  title: string;
  prompt: string;
  concepts: string[];
  order_matters: boolean;
  reference_sql: string;
  hints: [string, string, string];
};

export type ColumnInfo = {
  name: string;
  data_type: string;
  nullable: boolean;
};

export type TablePreview = {
  name: string;
  columns: ColumnInfo[];
  sample_columns: string[];
  sample_rows: unknown[][];
};

export type ExerciseDetail = ExerciseSummary & {
  prompt: string;
  schema: TablePreview[];
};

export type QueryResult = {
  columns: string[] | null;
  rows: unknown[][] | null;
  error: string | null;
  correct?: boolean | null;
  row_count?: number;
  expected_row_count?: number;
  column_match?: boolean;
  detail?: string | null;
  plan?: {
    steps: { op: string; label: string; detail: string }[];
    mermaid: string;
    frames?: {
      op: string;
      label: string;
      detail: string;
      row_count?: number | null;
      dropped?: number | null;
      columns?: string[] | null;
      selected_columns?: string[] | null;
      rows?: unknown[][] | null;
    }[];
  } | null;
};

export type HintResponse = QueryResult & {
  note: string;
  level: number;
  source: "coach" | "notes";
};

export type AskResponse = {
  answer: string;
  source: "coach" | "notes";
};
