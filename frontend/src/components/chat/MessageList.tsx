import { useEffect, useRef } from "react";

import { MessageBubble } from "./MessageBubble";

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

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onDeleteTurn={onDeleteTurn}
        />
      ))}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-muted rounded-2xl px-4 py-3 text-sm text-muted-foreground">
            Claude is thinking...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
