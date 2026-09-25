import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { QueryResult } from "@/types";

function renderCell(value: unknown) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function rowLabel(count: number): string {
  return count === 1 ? "1 row" : `${count} rows`;
}

export default function ResultPane({ result }: { result: QueryResult | null }) {
  const hasError = result != null && result.error != null;
  const correct = result != null && result.error == null && result.correct === true;
  const wrong = result != null && result.error == null && result.correct === false;
  const columns = result != null && result.error == null ? result.columns : null;
  const rows = result != null && result.error == null ? result.rows : null;
  const showTable = columns != null && rows != null && rows.length > 0;
  const showNoRows = columns != null && (rows == null || rows.length === 0);

  return (
    <section
      aria-live="polite"
      className="flex min-h-48 min-w-0 flex-col gap-3 overflow-auto"
    >
      {!result ? (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>Run the query to see rows here.</EmptyTitle>
          </EmptyHeader>
        </Empty>
      ) : null}
      {hasError ? (
        <Alert variant="destructive">
          <AlertTitle>Postgres rejected the query.</AlertTitle>
          <AlertDescription>
            <span className="font-mono">{result.error}</span>
          </AlertDescription>
        </Alert>
      ) : null}
      {correct ? (
        <Alert className="flex flex-row flex-wrap items-center gap-2">
          <Badge>Correct</Badge>
          <AlertTitle>That result matches.</AlertTitle>
        </Alert>
      ) : null}
      {wrong ? (
        <Alert variant="destructive">
          <AlertTitle>Result does not match.</AlertTitle>
          <AlertDescription>
            {rowLabel(result.row_count ?? 0)} returned, {rowLabel(result.expected_row_count ?? 0)}{" "}
            expected.
            {result.detail ? ` ${result.detail}` : null}
          </AlertDescription>
        </Alert>
      ) : null}
      {showTable && columns && rows ? (
        <Table className="font-mono text-sm">
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column} className="text-xs">
                  {column}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, rowIndex) => (
              <TableRow key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <TableCell key={cellIndex}>{renderCell(cell)}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
      {showNoRows ? <p className="font-mono text-sm">No rows.</p> : null}
    </section>
  );
}
