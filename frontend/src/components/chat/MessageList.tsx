import { Fragment, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";

import { MessageBubble } from "./MessageBubble";
import { ToolCallCard } from "./ToolCallCard";

import type { Message } from "@/api";

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  onDeleteTurn?: (turnUuid: string) => void;
}

export function MessageList({
  messages,
  isLoading,
  onDeleteTurn,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const bottom = bottomRef.current;
    if (!container || !bottom) return;
    // Scroll only inside the message list container instead of the whole page.
    const top = bottom.offsetTop;
    container.scrollTo({ top, behavior: "smooth" });
  }, [messages, isLoading]);

  // Group consecutive tool messages so they don't pile up as many cards.
  const groups = groupMessages(messages);

  return (
    <div
      ref={containerRef}
      className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4"
    >
      <div className="max-w-4xl mx-auto w-full space-y-4">
        {groups.map((item, idx) =>
          typeof item === "string" ? (
            // A single non-tool message id.
            <MessageBubble
              key={item}
              message={messages.find((m) => m.id === item)!}
              onDeleteTurn={onDeleteTurn}
            />
          ) : (
            <ToolGroup
              key={`toolgroup-${idx}`}
              tools={item.map((id) => messages.find((m) => m.id === id)!)}
            />
          ),
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl px-4 py-3 text-sm text-muted-foreground">
              Claude is thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

type GroupItem = string | string[];

/** Partition messages into single-message ids and runs of tool-message ids. */
function groupMessages(messages: Message[]): GroupItem[] {
  const out: GroupItem[] = [];
  let run: string[] = [];
  const flush = () => {
    if (run.length === 1) {
      out.push(run[0]);
    } else if (run.length > 1) {
      out.push(run);
    }
    run = [];
  };
  for (const m of messages) {
    if (m.role === "tool") {
      run.push(m.id);
    } else {
      flush();
      out.push(m.id);
    }
  }
  flush();
  return out;
}

/** A collapsible cluster of tool calls. Stays tiny by default. */
function ToolGroup({ tools }: { tools: Message[] }) {
  const [open, setOpen] = useState(false);
  if (tools.length === 0) return null;
  // A lone tool still renders as the compact card directly.
  if (tools.length === 1) {
    const t = tools[0];
    return (
      <ToolCallCard name={t.tool_name || "tool"} input={t.tool_input || {}} />
    );
  }
  return (
    <div className="rounded-lg border border-border bg-background/60">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 px-3 py-1 text-[11px] text-muted-foreground text-left hover:bg-muted/40"
      >
        {open ? (
          <ChevronDown className="h-3 w-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 flex-shrink-0" />
        )}
        <Wrench className="h-3 w-3 flex-shrink-0" />
        <span>
          {tools.length} {tools.length === 1 ? "tool call" : "tool calls"}
        </span>
      </button>
      {open && (
        <div className="space-y-1.5 px-2 pb-2">
          {tools.map((t) => (
            <Fragment key={t.id}>
              <ToolCallCard
                name={t.tool_name || "tool"}
                input={t.tool_input || {}}
              />
            </Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
