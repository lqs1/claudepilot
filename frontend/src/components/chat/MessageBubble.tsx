import { useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ChevronDown,
  ChevronRight,
  Sparkles,
  Trash2,
  User,
} from "lucide-react";

import { cn } from "@/lib/utils";

import type { Message } from "@/api";

interface MessageBubbleProps {
  message: Message;
  onDeleteTurn?: (turnUuid: string) => void;
}

export function MessageBubble({ message, onDeleteTurn }: MessageBubbleProps) {
  const { i18n } = useTranslation();
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  // A user prompt shares its uuid with the assistant reply of the same turn,
  // so deletion is anchored on user messages.
  const canDelete = isUser && !!message.uuid && !!onDeleteTurn;

  return (
    <div
      className={cn(
        "group flex w-full items-start gap-2",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {/* Assistant/tool avatar on the left */}
      {!isUser && <Avatar kind="assistant" />}

      <div className="relative">
        {canDelete && (
          <button
            type="button"
            onClick={() => onDeleteTurn?.(message.uuid!)}
            title="Delete this turn"
            className="absolute -left-9 top-1/2 -translate-y-1/2 hidden rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-destructive group-hover:block group-hover:opacity-100"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
        <div
          className={cn(
            "max-w-[80%] rounded-2xl px-4 py-3 shadow-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : isTool
                ? "bg-amber-50 text-amber-900 border border-amber-200 dark:bg-amber-950 dark:text-amber-100 dark:border-amber-900"
                : "bg-card text-card-foreground border border-border",
          )}
        >
          {isUser && (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </p>
          )}

          {message.role === "assistant" && (
            <>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content || " "}
                </ReactMarkdown>
              </div>
              {message.tool_uses && message.tool_uses.length > 0 && (
                <div className="mt-2 space-y-2 not-prose">
                  {message.tool_uses.map((tool) => (
                    <ToolCallCard
                      key={tool.id}
                      name={tool.name}
                      input={tool.input}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {isTool && (
            <div className="not-prose">
              <ToolCallCard
                name={message.tool_name || "tool"}
                input={message.tool_input || {}}
              />
            </div>
          )}

          <div
            className={cn(
              "text-[10px] mt-1 opacity-60",
              isUser ? "text-right" : "text-left",
            )}
          >
            {new Date(message.created_at).toLocaleTimeString(i18n.language)}
          </div>
        </div>
      </div>

      {/* User avatar on the right */}
      {isUser && <Avatar kind="user" />}
    </div>
  );
}

/** Small circular avatar distinguishing speakers. */
function Avatar({ kind }: { kind: "user" | "assistant" }) {
  if (kind === "user") {
    return (
      <span className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        <User className="h-4 w-4" />
      </span>
    );
  }
  return (
    <span className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white shadow-sm">
      <Sparkles className="h-4 w-4" />
    </span>
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

function ToolCallCard({
  name,
  input,
}: {
  name: string;
  input: Record<string, unknown>;
}) {
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
