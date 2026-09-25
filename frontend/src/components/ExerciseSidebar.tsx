import { CheckIcon, LockIcon } from "lucide-react";
import type { ExerciseSummary } from "../types";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const LOCKED_HINT = "Pass the previous exercise to open this one.";

type ExerciseSidebarProps = {
  exercises: ExerciseSummary[];
  index: number;
  openThrough: number;
  passed: Set<string>;
  loading: boolean;
  generating: boolean;
  canContinue: boolean;
  onContinue: () => void;
  onIndex: (index: number) => void;
};

export default function ExerciseSidebar({
  exercises,
  index,
  openThrough,
  passed,
  loading,
  generating,
  canContinue,
  onContinue,
  onIndex,
}: ExerciseSidebarProps) {
  const current = exercises[index];
  const dataset = current?.dataset ?? "Northline";
  const concepts = current?.concepts ?? [];
  const nextLocked = index < exercises.length - 1 && index >= openThrough;
  const showFooter = generating || canContinue || nextLocked;

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex flex-col gap-1 px-2">
          <p className="font-display">SQL Coach</p>
          <p className="truncate text-xs text-sidebar-foreground/70">{dataset}</p>
        </div>
      </SidebarHeader>
      <SidebarSeparator />
      <SidebarContent className="overflow-hidden">
        <ScrollArea className="h-full min-h-0">
          <SidebarGroup>
            <SidebarGroupLabel>Exercises</SidebarGroupLabel>
            {concepts.length > 0 ? (
              <p className="truncate px-2 text-xs text-sidebar-foreground/70" title={concepts.join(", ")}>
                {concepts.join(" · ")}
              </p>
            ) : null}
            <SidebarGroupContent>
              <SidebarMenu>
                {loading
                  ? Array.from({ length: 6 }, (_, row) => (
                      <SidebarMenuItem key={row}>
                        <SidebarMenuSkeleton showIcon />
                      </SidebarMenuItem>
                    ))
                  : exercises.map((exercise, optionIndex) => {
                      const locked = optionIndex > openThrough;
                      const isPassed = passed.has(exercise.id);
                      const isCurrent = optionIndex === index;
                      const button = (
                        <SidebarMenuButton
                          type="button"
                          isActive={isCurrent}
                          disabled={locked}
                          onClick={() => {
                            if (!locked) onIndex(optionIndex);
                          }}
                        >
                          <span className="tabular-nums">{optionIndex + 1}</span>
                          {locked ? <LockIcon /> : null}
                          {isPassed ? <CheckIcon /> : null}
                          <span>{exercise.title}</span>
                        </SidebarMenuButton>
                      );

                      return (
                        <SidebarMenuItem key={exercise.id}>
                          {locked ? (
                            <Tooltip>
                              <TooltipTrigger
                                render={
                                  <span className="block w-full" title={LOCKED_HINT} />
                                }
                              >
                                {button}
                              </TooltipTrigger>
                              <TooltipContent side="right">{LOCKED_HINT}</TooltipContent>
                            </Tooltip>
                          ) : (
                            button
                          )}
                        </SidebarMenuItem>
                      );
                    })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </ScrollArea>
      </SidebarContent>
      {showFooter ? (
        <>
          <SidebarSeparator />
          <SidebarFooter>
            {generating ? (
              <div className="flex items-center gap-2 px-2">
                <Skeleton className="size-4" />
                <p className="text-sidebar-foreground/80">Writing the next exercise…</p>
              </div>
            ) : canContinue ? (
              <Button type="button" variant="secondary" className="w-full" onClick={onContinue}>
                Write the next exercise
              </Button>
            ) : (
              <p className="px-2 text-sidebar-foreground/80">
                Pass this exercise to open the next one.
              </p>
            )}
          </SidebarFooter>
        </>
      ) : null}
    </Sidebar>
  );
}
