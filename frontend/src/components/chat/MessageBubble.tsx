import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

import type { Message } from "@/api";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { i18n } = useTranslation();
  const isUser = message.role === "user";
  const isTool = message.role === "tool";

  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
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
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content || " "}
            </ReactMarkdown>
          </div>
        )}

        {isTool && (
          <div className="text-sm">
            <div className="font-medium mb-1">🔧 {message.tool_name}</div>
            <pre className="text-xs bg-black/5 dark:bg-white/5 p-2 rounded overflow-auto">
              {JSON.stringify(message.tool_input, null, 2)}
            </pre>
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
  );
}
