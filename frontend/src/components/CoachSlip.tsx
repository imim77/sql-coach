import { useEffect, useState } from "react";
import { Loader2Icon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import type { HintResponse } from "@/types";

type CoachSlipProps = {
  hint: HintResponse | null;
  solution: string | null;
  busy: boolean;
  canHint: boolean;
  onHint: () => void;
  onSolution: () => void;
};

export default function CoachSlip({
  hint,
  solution,
  busy,
  canHint,
  onHint,
  onSolution,
}: CoachSlipProps) {
  const [hinting, setHinting] = useState(false);

  useEffect(() => {
    if (!busy) setHinting(false);
  }, [busy]);

  return (
    <aside className="flex min-h-0 min-w-0 flex-col">
      <Card className="min-h-0 flex-1">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Avatar className="size-8">
              <AvatarFallback>C</AvatarFallback>
            </Avatar>
            <div className="flex min-w-0 flex-col gap-1">
              <CardTitle>Coach</CardTitle>
              <CardDescription>
                A note on what the result is doing. It never includes the query.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {hint ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {hint.source === "coach" ? "Coach" : "Saved note"}
                </Badge>
                <span className="text-xs text-muted-foreground">Note {hint.level} of 3</span>
              </div>
              <Progress value={(hint.level / 3) * 100} />
              <div className="rounded-lg bg-muted p-3 text-sm leading-relaxed">{hint.note}</div>
            </div>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyDescription>Run a query, then ask for a note.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {solution != null ? (
            <>
              <Separator />
              <div className="flex flex-col gap-2">
                <div className="text-xs font-medium">Solution</div>
                <pre className="overflow-auto rounded-lg bg-muted p-3 font-mono text-xs leading-5">
                  {solution}
                </pre>
              </div>
            </>
          ) : null}
        </CardContent>
        <CardFooter className="flex-wrap gap-2">
          <Button
            type="button"
            disabled={!canHint || busy}
            onClick={() => {
              setHinting(true);
              onHint();
            }}
          >
            {hinting ? <Loader2Icon data-icon="inline-start" className="animate-spin" /> : null}
            Hint
          </Button>
          {solution == null ? (
            <Button type="button" variant="ghost" disabled={busy} onClick={onSolution}>
              Show solution
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    </aside>
  );
}
