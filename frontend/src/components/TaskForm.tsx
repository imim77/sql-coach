import { useState, type ComponentProps, type FormEvent } from "react";
import { createTask } from "@/api";
import type { CreateTaskRequest, ExerciseSummary } from "@/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const labelClass = "text-sm leading-none font-medium";

const textareaClass =
  "min-h-20 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40";

type TaskFormProps = {
  onCreated: (exercise: ExerciseSummary) => void | Promise<void>;
};

function TaskTextarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(textareaClass, className)} {...props} />;
}

function conceptsOf(value: string): string[] {
  return value
    .split(",")
    .map((name) => name.trim())
    .filter((name) => name.length > 0);
}

export default function TaskForm({ onCreated }: TaskFormProps) {
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [concepts, setConcepts] = useState("");
  const [prompt, setPrompt] = useState("");
  const [referenceSql, setReferenceSql] = useState("");
  const [hints, setHints] = useState<[string, string, string]>(["", "", ""]);
  const [orderMatters, setOrderMatters] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateHint(index: 0 | 1 | 2, value: string) {
    setHints((current) => {
      const next: [string, string, string] = [current[0], current[1], current[2]];
      next[index] = value;
      return next;
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const body: CreateTaskRequest = {
      id: id.trim(),
      title: title.trim(),
      prompt: prompt.trim(),
      concepts: conceptsOf(concepts),
      order_matters: orderMatters,
      reference_sql: referenceSql.trim(),
      hints: [hints[0].trim(), hints[1].trim(), hints[2].trim()],
    };
    setPending(true);
    setError(null);
    try {
      const created = await createTask(body);
      await onCreated(created);
      setId("");
      setTitle("");
      setConcepts("");
      setPrompt("");
      setReferenceSql("");
      setHints(["", "", ""]);
      setOrderMatters(false);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="flex flex-col gap-4 px-4 pb-4" onSubmit={onSubmit}>
      <div className="flex flex-col gap-2">
        <label htmlFor="task-id" className={labelClass}>
          Id
        </label>
        <Input
          id="task-id"
          value={id}
          onChange={(event) => setId(event.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="task-title" className={labelClass}>
          Title
        </label>
        <Input id="task-title" value={title} onChange={(event) => setTitle(event.target.value)} />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="task-concepts" className={labelClass}>
          Concepts
        </label>
        <Input
          id="task-concepts"
          value={concepts}
          onChange={(event) => setConcepts(event.target.value)}
          placeholder="filter, semi-join"
          autoComplete="off"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="task-prompt" className={labelClass}>
          Prompt
        </label>
        <TaskTextarea id="task-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="task-reference-sql" className={labelClass}>
          Reference SQL
        </label>
        <TaskTextarea
          id="task-reference-sql"
          value={referenceSql}
          onChange={(event) => setReferenceSql(event.target.value)}
          spellCheck={false}
          className="min-h-28 font-mono"
        />
      </div>
      {([0, 1, 2] as const).map((index) => (
        <div key={index} className="flex flex-col gap-2">
          <label htmlFor={`task-hint-${index + 1}`} className={labelClass}>
            Hint {index + 1}
          </label>
          <Input
            id={`task-hint-${index + 1}`}
            value={hints[index]}
            onChange={(event) => updateHint(index, event.target.value)}
          />
        </div>
      ))}
      <label htmlFor="task-order-matters" className="flex items-center gap-2 text-sm leading-none font-medium">
        <input
          id="task-order-matters"
          type="checkbox"
          checked={orderMatters}
          onChange={(event) => setOrderMatters(event.target.checked)}
          className="size-4 accent-primary"
        />
        Row order matters
      </label>
      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <Button type="submit" disabled={pending} className="w-full">
        Add a task
      </Button>
    </form>
  );
}
