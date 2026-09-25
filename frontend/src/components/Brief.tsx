import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
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
    <Table className="font-mono text-sm">
      <TableHeader>
        <TableRow>
          {table.sample_columns.map((column) => (
            <TableHead key={column} className="text-xs">
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
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-5 w-20" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </section>
    );
  }

  return (
    <section className="min-h-0 min-w-0 overflow-auto">
      <div className="flex flex-col gap-4">
        <p className="font-mono text-xs text-muted-foreground">{exercise.dataset}</p>
        <h1 className="font-display text-2xl tracking-tight">{exercise.title}</h1>
        <div className="flex flex-wrap gap-2">
          {exercise.concepts.map((concept) => (
            <Badge key={concept} variant="secondary">
              {concept}
            </Badge>
          ))}
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{exercise.prompt}</p>
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium">Tables</h2>
          {exercise.schema.length > 0 ? (
            <Accordion defaultValue={[exercise.schema[0].name]}>
              {exercise.schema.map((table) => (
                <AccordionItem key={table.name} value={table.name}>
                  <AccordionTrigger>
                    <span className="font-mono">{table.name}</span>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="flex flex-col gap-3">
                      <ul className="flex flex-col gap-1 font-mono text-muted-foreground">
                        {table.columns.map((column) => (
                          <li key={column.name}>
                            {column.name} {column.data_type}
                            {column.nullable ? " null" : ""}
                          </li>
                        ))}
                      </ul>
                      <SampleTable table={table} />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          ) : null}
        </div>
      </div>
    </section>
  );
}
