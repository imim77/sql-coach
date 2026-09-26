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
import type { AskResponse, HintResponse } from "@/types";

const questionClass =
  "min-h-16 w-full resize-y rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm font-normal transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50";

type CoachSlipProps = {
  hint: HintResponse | null;
  busy: boolean;
  canAsk: boolean;
  asking: boolean;
  answer: AskResponse | null;
  question: string;
  onQuestion: (value: string) => void;
  onAsk: () => void;
  onHint: () => void;
};

export default function CoachSlip({
  hint,
  busy,
  canAsk,
  asking,
  answer,
  question,
  onQuestion,
  onAsk,
  onHint,
}: CoachSlipProps) {
  const [hinting, setHinting] = useState(false);

  useEffect(() => {
    if (!busy) setHinting(false);
  }, [busy]);

  return (
    <aside className="flex min-h-0 min-w-0 flex-col">
      <Card className="rounded-none border-0 ring-0">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Avatar className="size-8">
              <AvatarFallback>C</AvatarFallback>
            </Avatar>
            <div className="flex min-w-0 flex-col gap-1">
              <CardTitle className="font-normal">Coach</CardTitle>
              <CardDescription>
                A hint explains the result. It never includes the query.
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
            <Empty className="flex-none gap-0 border-0 p-0">
              <EmptyHeader>
                <EmptyDescription>
                  {canAsk
                    ? "Ask for a hint about the query you wrote."
                    : "Write a query on the right, then ask for a hint."}
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {answer ? (
            <div className="flex flex-col gap-2">
              <Badge variant="secondary">{answer.source === "coach" ? "Coach" : "Saved note"}</Badge>
              <div className="rounded-lg bg-muted p-3 text-sm leading-relaxed">{answer.answer}</div>
            </div>
          ) : null}
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3">
          <label className="flex flex-col gap-2 text-sm font-medium" htmlFor="coach-question">
            Ask the coach
            <textarea
              id="coach-question"
              rows={3}
              value={question}
              placeholder="What do you want the result to show?"
              onChange={(event) => onQuestion(event.target.value)}
              className={questionClass}
            />
          </label>
          <Button
            type="button"
            className="self-start"
            disabled={!canAsk || busy || asking || question.trim().length === 0}
            onClick={onAsk}
          >
            {asking ? <Loader2Icon data-icon="inline-start" className="animate-spin" /> : null}
            Ask
          </Button>
          <Button
            type="button"
            className="self-start"
            disabled={!canAsk || busy}
            onClick={() => {
              setHinting(true);
              onHint();
            }}
          >
            {hinting ? <Loader2Icon data-icon="inline-start" className="animate-spin" /> : null}
            Ask for a hint
          </Button>
        </CardFooter>
      </Card>
    </aside>
  );
}
