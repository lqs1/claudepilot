import { useEffect, useRef } from "react";

import { MessageBubble } from "./MessageBubble";

import type { Message } from "@/api";

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
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
