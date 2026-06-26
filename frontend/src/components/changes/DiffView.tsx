import { useState } from "react";

import type { ChangeEntry } from "@/api";

interface DiffViewProps {
  change: ChangeEntry;
}

/**
 * Renders a single change: a header line (kind/file) plus the before/after.
 * For edits we show the server-computed unified diff with -/+ coloring,
 * including a clean before/after fallback. For creates we show the new file.
 */
export function DiffView({ change }: DiffViewProps) {
  const [mode, setMode] = useState<"diff" | "after">(
    change.kind === "create" ? "after" : "diff",
  );

  return (
    <div className="rounded-lg border border-border overflow-hidden bg-card">
      <div className="flex items-center justify-between px-3 py-1.5 bg-muted/40 border-b border-border">
        <span className="text-xs font-medium text-muted-foreground">
          {change.kind === "create" ? "Created" : "Edited"} · #
          {change.order + 1}
        </span>
        {change.kind === "edit" && (
          <div className="flex gap-1">
            <ModeBtn active={mode === "diff"} onClick={() => setMode("diff")}>
              Diff
            </ModeBtn>
            <ModeBtn active={mode === "after"} onClick={() => setMode("after")}>
              Result
            </ModeBtn>
          </div>
        )}
      </div>

      {mode === "diff" && change.kind === "edit" ? (
        <DiffLines diff={change.diff} />
      ) : (
        <CodeBlock text={change.new_text} />
      )}
    </div>
  );
}

function ModeBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded px-2 py-0.5 text-xs transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}

function DiffLines({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className="text-xs font-mono overflow-x-auto max-h-[50vh] overflow-y-auto">
      {lines.map((line, i) => {
        let cls = "text-foreground";
        if (line.startsWith("+++") || line.startsWith("---"))
          cls = "text-muted-foreground font-semibold";
        else if (line.startsWith("+"))
          cls = "bg-green-500/15 text-green-700 dark:text-green-400";
        else if (line.startsWith("-"))
          cls = "bg-red-500/15 text-red-700 dark:text-red-400";
        else if (line.startsWith("@@"))
          cls = "text-blue-600 dark:text-blue-400";
        return (
          <div key={i} className={`px-3 whitespace-pre ${cls}`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

function CodeBlock({ text }: { text: string }) {
  return (
    <pre className="text-xs font-mono overflow-x-auto max-h-[50vh] overflow-y-auto px-3 py-2">
      {text || " "}
    </pre>
  );
}
