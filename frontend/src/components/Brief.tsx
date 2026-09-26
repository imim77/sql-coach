import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ExerciseDetail, TablePreview } from "@/types";

function renderCell(value: unknown) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function SampleTable({ table }: { table: TablePreview }) {
  return (
    <Table className="font-mono text-sm font-normal">
      <TableHeader>
        <TableRow>
          {table.sample_columns.map((column) => (
            <TableHead key={column} className="font-mono text-xs font-normal">
              {column}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {table.sample_rows.map((row, rowIndex) => (
          <TableRow key={rowIndex}>
            {row.map((cell, cellIndex) => (
              <TableCell key={cellIndex}>{renderCell(cell)}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function Brief({ exercise }: { exercise: ExerciseDetail | null }) {
  if (!exercise) {
    return (
      <section className="min-h-0 min-w-0 overflow-auto">
        <div className="flex flex-col gap-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </section>
    );
  }

  return (
    <section className="min-h-0 min-w-0 overflow-auto">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4">
          <p className="font-mono text-xs text-muted-foreground">{exercise.dataset}</p>
          <h1 className="font-display text-2xl font-normal tracking-tight">{exercise.title}</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Assignment</CardTitle>
          </CardHeader>
          <CardContent className="whitespace-pre-wrap">{exercise.prompt}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Tables</CardTitle>
          </CardHeader>
          <CardContent>
          {exercise.schema.length > 0 ? (
            <Accordion defaultValue={[exercise.schema[0].name]}>
              {exercise.schema.map((table) => (
                <AccordionItem key={table.name} value={table.name}>
                  <AccordionTrigger>
                    <span className="font-mono font-normal">{table.name}</span>
                  </AccordionTrigger>
                  <AccordionContent>
                    <SampleTable table={table} />
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          ) : null}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
