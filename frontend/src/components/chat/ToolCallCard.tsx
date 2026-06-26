import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface ToolCallCardProps {
  name: string;
  input: Record<string, unknown>;
}

/** A compact, collapsed-by-default tool call card. Shows a small one-line
 * summary (Bash + command, Read/Write + file path) and reveals the full input
 * only on click, so runs of many tool calls don't dominate the chat. */
export function ToolCallCard({ name, input }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const summary = toolSummary(input);
  return (
    <div className="rounded-lg border border-border bg-background/60">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-1.5 px-3 py-1 text-[11px] text-muted-foreground text-left hover:bg-muted/40"
        title={name}
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 flex-shrink-0" />
        )}
        <span className="font-medium">{name}</span>
        {summary && (
          <span className="truncate text-foreground/60">{summary}</span>
        )}
      </button>
      {expanded && (
        <pre className="text-[11px] font-mono bg-black/5 dark:bg-white/5 px-3 py-2 rounded-b-lg overflow-auto max-h-60 border-t border-border">
          {JSON.stringify(input, null, 2)}
        </pre>
      )}
    </div>
  );
}

function toolSummary(input: Record<string, unknown>): string {
  // Give a concise, meaningful one-liner instead of always dumping JSON.
  const cmd = input.command;
  if (typeof cmd === "string") return cmd;
  const fp = input.file_path;
  if (typeof fp === "string") return fp;
  if (typeof input.path === "string") return input.path;
  return "";
}
