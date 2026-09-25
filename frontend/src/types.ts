export type ExerciseSummary = {
  id: string;
  title: string;
  concepts: string[];
  dataset: string;
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
};

export type HintResponse = QueryResult & {
  note: string;
  level: number;
  source: "coach" | "notes";
};
