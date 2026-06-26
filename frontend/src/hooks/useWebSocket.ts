import { useEffect, useRef, useCallback, useState } from "react";

import { useAppStore } from "@/stores/appStore";

export type ClaudeStatus = "idle" | "thinking" | "writing" | "error" | null;

interface WebSocketMessage {
  type: string;
  session_id?: string;
  data?: Record<string, unknown>;
}

export interface ClaudeEventHandler {
  onAssistant?: (sessionId: string, data: Record<string, unknown>) => void;
  onPermissionRequest?: (
    sessionId: string,
    data: Record<string, unknown>,
  ) => void;
  onAskUserQuestion?: (
    sessionId: string,
    toolUseId: string,
    data: Record<string, unknown>,
  ) => void;
  onStatus?: (sessionId: string, data: Record<string, unknown>) => void;
  onPlan?: (sessionId: string, data: Record<string, unknown>) => void;
  onError?: (sessionId: string, data: Record<string, unknown>) => void;
}

export function useWebSocket(handler?: ClaudeEventHandler) {
  const ws = useRef<WebSocket | null>(null);
  const handlerRef = useRef(handler);
  const pendingSubscriptions = useRef<Set<string>>(new Set());
  const seenMessageIds = useRef<Record<string, Set<string>>>({});
  const sessionHasAssistantContent = useRef<Record<string, boolean>>({});
  const [status, setStatus] = useState<ClaudeStatus>(null);

  const addMessage = useAppStore((state) => state.addMessage);
  const updateMessage = useAppStore((state) => state.updateMessage);

  // Active subscriptions survive reconnects.
  const activeSubscriptions = useRef<Set<string>>(new Set());
  const currentSessionIdRef = useRef<string | null>(null);

  // Update handlerRef in useEffect instead of render phase for React 19 safety
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.onopen = () => {
      console.log("WebSocket connected, version 2");
      // Re-subscribe all active sessions on reconnect.
      for (const sessionId of activeSubscriptions.current) {
        socket.send(
          JSON.stringify({ type: "subscribe", session_id: sessionId }),
        );
      }
      // Send any pending subscriptions requested before connection.
      for (const sessionId of pendingSubscriptions.current) {
        activeSubscriptions.current.add(sessionId);
        socket.send(
          JSON.stringify({ type: "subscribe", session_id: sessionId }),
        );
      }
      pendingSubscriptions.current.clear();
    };

    socket.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data);
        if (msg.type === "claude_event" && msg.session_id && msg.data) {
          handleClaudeEvent(msg.session_id, msg.data);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message", err);
      }
    };

    socket.onclose = () => {
      console.log("WebSocket disconnected");
      ws.current = null;
      setTimeout(connect, 2000);
    };

    socket.onerror = (err) => {
      console.error("WebSocket error", err);
    };

    ws.current = socket;
  }, []);

  const subscribe = useCallback((sessionId: string) => {
    currentSessionIdRef.current = sessionId;
    activeSubscriptions.current.add(sessionId);
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({ type: "subscribe", session_id: sessionId }),
      );
    } else {
      pendingSubscriptions.current.add(sessionId);
    }
  }, []);

  const unsubscribe = useCallback((sessionId: string) => {
    if (currentSessionIdRef.current === sessionId) {
      currentSessionIdRef.current = null;
      setStatus(null);
    }
    activeSubscriptions.current.delete(sessionId);
    pendingSubscriptions.current.delete(sessionId);
    // Clear session tracking state when unsubscribing to prevent stale data
    delete sessionHasAssistantContent.current[sessionId];
    delete seenMessageIds.current[sessionId];
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({ type: "unsubscribe", session_id: sessionId }),
      );
    }
  }, []);

  const handleClaudeEvent = (
    sessionId: string,
    data: Record<string, unknown>,
  ) => {
    const eventType = data.type as string;
    const currentHandler = handlerRef.current;

    if (eventType === "assistant") {
      const messageId = data.message_id as string | undefined;
      const text = (data.text as string) || "";
      const toolUses =
        (data.tool_uses as Array<{
          id: string;
          name: string;
          input: Record<string, unknown>;
        }>) || [];
      const sessionSeen =
        seenMessageIds.current[sessionId] ?? new Set<string>();
      seenMessageIds.current[sessionId] = sessionSeen;

      // Handle text content
      if (messageId && sessionSeen.has(messageId)) {
        // Update existing message with new text
        if (text) {
          updateMessage(sessionId, messageId, { content: text });
        }
      } else if (text || toolUses.length > 0) {
        // New message — show even if text is empty but has tool uses
        if (messageId) {
          sessionSeen.add(messageId);
        }
        if (text) {
          sessionHasAssistantContent.current[sessionId] = true;
        }
        addMessage(sessionId, {
          id:
            messageId ||
            `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          session_id: sessionId,
          role: "assistant",
          type: "text",
          content: text,
          created_at: new Date().toISOString(),
        });
      }

      // Handle tool uses
      for (const tool of toolUses) {
        addMessage(sessionId, {
          id: tool.id,
          session_id: sessionId,
          role: "tool",
          type: "tool_use",
          content: `Using tool: ${tool.name}`,
          tool_name: tool.name,
          tool_input: tool.input,
          created_at: new Date().toISOString(),
        });

        if (
          tool.name === "AskUserQuestion" &&
          currentHandler?.onAskUserQuestion
        ) {
          currentHandler.onAskUserQuestion(sessionId, tool.id, tool.input);
        }
      }

      currentHandler?.onAssistant?.(sessionId, data);
    } else if (eventType === "permission_request") {
      currentHandler?.onPermissionRequest?.(sessionId, data);
    } else if (eventType === "status") {
      const nextStatus = (data.status as ClaudeStatus) || null;
      if (currentSessionIdRef.current === sessionId) {
        setStatus(nextStatus);
      }
      currentHandler?.onStatus?.(sessionId, data);
    } else if (eventType === "plan") {
      currentHandler?.onPlan?.(sessionId, data);
    } else if (eventType === "error") {
      console.error("Claude event error:", data);
      currentHandler?.onError?.(sessionId, data);
    } else if (eventType === "result") {
      // Only add result as fallback when no assistant content was received
      const result = (data.result as string) || "";
      if (result && !sessionHasAssistantContent.current[sessionId]) {
        sessionHasAssistantContent.current[sessionId] = true;
        addMessage(sessionId, {
          id: `result-${Date.now()}`,
          session_id: sessionId,
          role: "assistant",
          type: "text",
          content: result,
          created_at: new Date().toISOString(),
        });
      }
      currentHandler?.onAssistant?.(sessionId, data);
    } else if (eventType === "raw_output") {
      const stream = data.stream as string;
      const content = (data.content as string) || "";
      console.log(`[Claude ${stream}]`, content.trim());
    }
  };

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  return { subscribe, unsubscribe, status };
}
