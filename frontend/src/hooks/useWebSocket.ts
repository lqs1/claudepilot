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
  onResult?: (sessionId: string, data: Record<string, unknown>) => void;
}

export function useWebSocket(handler?: ClaudeEventHandler) {
  const ws = useRef<WebSocket | null>(null);
  const handlerRef = useRef(handler);
  const pendingSubscriptions = useRef<Set<string>>(new Set());
  const seenMessageIds = useRef<Record<string, Set<string>>>({});
  const sessionHasAssistantContent = useRef<Record<string, boolean>>({});
  // Per-session status so several parallel sessions can each be tracked at
  // once. Drives the global loadingSessions set (halo/sidebar indicators).
  const [statuses, setStatuses] = useState<Record<string, ClaudeStatus>>({});

  const addMessage = useAppStore((state) => state.addMessage);
  const updateMessage = useAppStore((state) => state.updateMessage);
  const setLoading = useAppStore((state) => state.setLoading);

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
    activeSubscriptions.current.delete(sessionId);
    pendingSubscriptions.current.delete(sessionId);
    // Drop this session's status so it no longer reads as busy, and sync the
    // global loading set.
    setStatuses((prev) => {
      if (!(sessionId in prev)) return prev;
      const next = { ...prev };
      delete next[sessionId];
      return next;
    });
    setLoading(sessionId, false);
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

      // Accumulate assistant text by message_id. We only create a bubble once
      // there is actual text — leading empty (thinking-only) events must NOT
      // spawn an empty placeholder, or a short/no-text reply leaves a blank
      // bubble behind. We still track the id so later chunks merge instead of
      // duplicating.
      if (messageId && text) {
        if (sessionSeen.has(messageId)) {
          updateMessage(sessionId, messageId, { content: text });
        } else {
          sessionSeen.add(messageId);
          addMessage(sessionId, {
            id: messageId,
            session_id: sessionId,
            role: "assistant",
            type: "text",
            content: text,
            created_at: new Date().toISOString(),
          });
        }
        sessionHasAssistantContent.current[sessionId] = true;
      } else if (messageId) {
        // Empty/thinking event — register the id but emit no bubble yet.
        sessionSeen.add(messageId);
      } else if (!messageId && text) {
        addMessage(sessionId, {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          session_id: sessionId,
          role: "assistant",
          type: "text",
          content: text,
          created_at: new Date().toISOString(),
        });
        sessionHasAssistantContent.current[sessionId] = true;
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
      // Record status per session so multiple parallel sessions are tracked
      // independently, and mirror busy state into the global loading set.
      setStatuses((prev) => ({ ...prev, [sessionId]: nextStatus }));
      setLoading(
        sessionId,
        nextStatus === "thinking" || nextStatus === "writing",
      );
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
      currentHandler?.onResult?.(sessionId, data);
    } else if (eventType === "raw_output") {
      const stream = data.stream as string;
      const content = (data.content as string) || "";
      console.log(`[Claude ${stream}]`, content.trim());
    }
  };

  useEffect(() => {
    connect();
    const pingId = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 20000);
    return () => {
      clearInterval(pingId);
      ws.current?.close();
    };
  }, [connect]);

  return {
    subscribe,
    unsubscribe,
    getStatus: (sessionId: string) => statuses[sessionId] ?? null,
  };
}
