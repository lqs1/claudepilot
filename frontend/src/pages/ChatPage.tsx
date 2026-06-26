import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Settings } from "lucide-react";

import { InputBox } from "@/components/chat/InputBox";
import { MessageList } from "@/components/chat/MessageList";
import { PermissionDialog } from "@/components/chat/PermissionDialog";
import { QuestionDialog } from "@/components/chat/QuestionDialog";
import { PlanModePanel } from "@/components/chat/PlanModePanel";
import { SessionSettings } from "@/components/settings/SessionSettings";
import { Button } from "@/components/ui/button";
import { messageApi } from "@/api";
import { useAppStore } from "@/stores/appStore";
import { useWebSocket, type ClaudeEventHandler } from "@/hooks/useWebSocket";
import { parsePlanSteps, mergeSteps, type PlanState } from "@/lib/plan";

function formatElapsed(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (totalSeconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function useSessionTimer(sessionId: string | null, isRunning: boolean) {
  const sessions = useAppStore((state) => state.sessions);
  const session = useMemo(
    () => sessions.find((s) => s.id === sessionId),
    [sessions, sessionId],
  );
  const startedAt = session?.started_at
    ? new Date(session.started_at).getTime()
    : null;
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startedAt || !isRunning) {
      setElapsed(0);
      return;
    }
    const update = () => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [startedAt, isRunning]);

  return isRunning && startedAt ? formatElapsed(elapsed) : "--:--";
}

function StatusIndicator({ status }: { status: string | null }) {
  if (!status) return null;
  const labels: Record<string, string> = {
    idle: "Idle",
    thinking: "Thinking",
    writing: "Writing",
    error: "Error",
  };
  const colors: Record<string, string> = {
    idle: "bg-green-500",
    thinking: "bg-amber-500 animate-pulse",
    writing: "bg-primary animate-pulse",
    error: "bg-red-500",
  };
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-2 py-1 text-xs font-medium text-foreground">
      <span
        className={`h-2 w-2 rounded-full ${colors[status] || "bg-muted"}`}
      />
      {labels[status] || status}
    </span>
  );
}
interface PermissionState {
  sessionId: string;
  toolUseId: string;
  tool: string;
  operation: string;
  reason: string;
}

interface QuestionState {
  sessionId: string;
  toolUseId: string;
  questions: Array<{
    question: string;
    header?: string;
    options: Array<{ value: string; label?: string }>;
    multi_select?: boolean;
  }>;
}

export function ChatPage() {
  const { t } = useTranslation();
  const {
    selectedSessionId,
    sessions,
    messages,
    addMessage,
    setMessages,
    removeTurn,
    language,
  } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [permission, setPermission] = useState<PermissionState | null>(null);
  const [question, setQuestion] = useState<QuestionState | null>(null);
  const [plan, setPlan] = useState<PlanState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const elapsed = useSessionTimer(selectedSessionId, isRunning);

  const handlePermissionRequest: ClaudeEventHandler["onPermissionRequest"] =
    useCallback((sessionId, data) => {
      setPermission({
        sessionId,
        toolUseId: (data.tool_use_id as string) || "",
        tool: (data.tool as string) || "",
        operation: (data.operation as string) || "",
        reason: (data.reason as string) || "",
      });
    }, []);

  const handleAskUserQuestion: ClaudeEventHandler["onAskUserQuestion"] =
    useCallback((sessionId, toolUseId, input) => {
      const questions =
        (input.questions as Array<Record<string, unknown>>) || [];
      setQuestion({
        sessionId,
        toolUseId,
        questions: questions.map((q) => ({
          question: (q.question as string) || "",
          header: (q.header as string) || undefined,
          options:
            (q.options as Array<{ value: string; label?: string }>) || [],
          multi_select: (q.multi_select as boolean) || false,
        })),
      });
    }, []);

  const handleError: ClaudeEventHandler["onError"] = useCallback(
    (_sessionId, data) => {
      setError((data.message as string) || "Claude error");
    },
    [],
  );

  const handlePlan: ClaudeEventHandler["onPlan"] = useCallback(
    (sessionId, data) => {
      const planMode = data.plan_mode as string;
      const planText = (data.plan as string) || "";

      if (planMode === "enter") {
        setPlan({
          sessionId,
          isActive: true,
          steps: [],
          rawPlan: planText,
        });
      } else if (planMode === "exit") {
        setPlan((prev) => (prev ? { ...prev, isActive: false } : null));
      } else {
        setPlan((prev) => {
          if (!prev) {
            return {
              sessionId,
              isActive: true,
              steps: parsePlanSteps(planText),
              rawPlan: planText,
            };
          }
          const newSteps = parsePlanSteps(planText);
          return {
            ...prev,
            sessionId,
            steps: mergeSteps(prev.steps, newSteps),
            rawPlan: planText,
          };
        });
      }
    },
    [],
  );

  const wsHandler: ClaudeEventHandler = {
    onPermissionRequest: handlePermissionRequest,
    onAskUserQuestion: handleAskUserQuestion,
    onError: handleError,
    onPlan: handlePlan,
  };

  const { subscribe, unsubscribe, status } = useWebSocket(wsHandler);
  const sessionMessages = selectedSessionId
    ? messages[selectedSessionId] || []
    : [];

  const loadMessages = useCallback(
    async (sessionId: string) => {
      try {
        const response = await messageApi.list(sessionId);
        setMessages(sessionId, response.data.messages);
      } catch (err) {
        console.error("Failed to load messages", err);
      }
    },
    [setMessages],
  );

  // Sync UI running state with the authoritative backend session status.
  // We must NOT infer "running" from the presence of assistant messages:
  // a session with history is not necessarily live, and that wrong guess
  // blocks operations (like history delete) that require a stopped session.
  useEffect(() => {
    if (!selectedSessionId) {
      setIsRunning(false);
      return;
    }
    const session = sessions.find((s) => s.id === selectedSessionId);
    setIsRunning(session?.status === "running");
  }, [selectedSessionId, sessions]);

  useEffect(() => {
    if (!selectedSessionId) return;

    subscribe(selectedSessionId);
    // Load history once per session. The WebSocket is the single source of
    // truth for live updates; we deliberately do NOT poll on an interval,
    // because the server persists messages asynchronously (fire-and-forget)
    // and a DB read can return a stale list that would clobber a reply that
    // just arrived over the WebSocket.
    loadMessages(selectedSessionId);

    return () => {
      unsubscribe(selectedSessionId);
    };
  }, [selectedSessionId, subscribe, unsubscribe, loadMessages]);

  const handleStartSession = async () => {
    if (!selectedSessionId) return;
    setError(null);
    try {
      await messageApi.resume(selectedSessionId);
      setIsRunning(true);
    } catch (err) {
      console.error("Failed to start session", err);
      setError(err instanceof Error ? err.message : "Failed to start session");
    }
  };

  const handleDeleteTurn = async (turnUuid: string) => {
    if (!selectedSessionId) return;
    const confirmed = window.confirm(
      t("chat.confirmDeleteTurn") ||
        "Delete this turn and its reply? This also removes it from the CLI history.",
    );
    if (!confirmed) return;
    setError(null);
    try {
      await messageApi.deleteTurn(selectedSessionId, turnUuid);
      removeTurn(selectedSessionId, turnUuid);
    } catch (err) {
      console.error("Failed to delete turn", err);
      // The backend rejects deletion with 409 while the engine is running
      // (it owns the jsonl file); surface that as a clear instruction.
      const isRunning =
        err instanceof Error && /409|Stop the session/.test(err.message);
      setError(
        isRunning
          ? t("chat.stopBeforeDelete") || "Stop the session before deleting"
          : err instanceof Error
            ? err.message
            : "Failed to delete turn",
      );
    }
  };

  const handleSend = async (content: string) => {
    if (!selectedSessionId) return;

    setError(null);
    addMessage(selectedSessionId, {
      id: `${Date.now()}-user`,
      session_id: selectedSessionId,
      role: "user",
      type: "text",
      content,
      created_at: new Date().toISOString(),
    });

    setIsLoading(true);
    abortRef.current = new AbortController();
    try {
      if (!isRunning) {
        await messageApi.resume(selectedSessionId);
        setIsRunning(true);
      }
      await messageApi.send(selectedSessionId, content);
    } catch (err) {
      console.error("Failed to send message", err);
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  };

  const handlePermissionRespond = async (
    sessionId: string,
    toolUseId: string,
    allowed: boolean,
  ) => {
    try {
      await messageApi.respondPermission(sessionId, toolUseId, allowed);
    } catch (err) {
      console.error("Failed to respond to permission request", err);
      setError(err instanceof Error ? err.message : "Failed to respond");
    }
    setPermission(null);
  };

  const handleQuestionAnswer = async (
    sessionId: string,
    toolUseId: string,
    answers: Array<Record<string, unknown>>,
  ) => {
    try {
      await messageApi.answer(sessionId, toolUseId, answers);
    } catch (err) {
      console.error("Failed to answer question", err);
      setError(err instanceof Error ? err.message : "Failed to answer");
    }
    setQuestion(null);
  };

  if (!selectedSessionId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        {t("session.newSession")}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-border bg-card">
        <div className="flex items-center gap-3 text-sm font-medium">
          <span>
            {t("session.title")} · {language.toUpperCase()}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {elapsed}
          </span>
          <StatusIndicator status={status} />
        </div>
        <div className="flex items-center gap-2">
          {error && (
            <span className="text-xs text-red-500" title={error}>
              Error
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSettings(true)}
            title={t("settings.sessionTitle")}
          >
            <Settings className="h-4 w-4" />
          </Button>
          <Button
            variant={isRunning ? "secondary" : "default"}
            size="sm"
            onClick={isRunning ? undefined : handleStartSession}
            disabled={isRunning}
          >
            {isRunning ? t("chat.stopSession") : t("chat.startSession")}
          </Button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-950 border-b border-red-200 dark:border-red-900">
          <p className="text-xs text-red-600 dark:text-red-300">{error}</p>
        </div>
      )}

      <MessageList
        messages={sessionMessages}
        isLoading={isLoading}
        onDeleteTurn={handleDeleteTurn}
      />
      {/* PlanModePanel only renders when there is an active plan, and is
          clamped so it can never push the input box off-screen. */}
      {plan?.isActive && (
        <div className="flex-shrink-0 min-h-0 max-h-[40vh] overflow-y-auto">
          <PlanModePanel plan={plan} onPlanChange={setPlan} />
        </div>
      )}
      <InputBox onSend={handleSend} disabled={isLoading} />

      <PermissionDialog
        isOpen={!!permission}
        sessionId={permission?.sessionId || ""}
        toolUseId={permission?.toolUseId || ""}
        tool={permission?.tool || ""}
        operation={permission?.operation || ""}
        reason={permission?.reason || ""}
        onRespond={handlePermissionRespond}
      />

      <QuestionDialog
        isOpen={!!question}
        sessionId={question?.sessionId || ""}
        toolUseId={question?.toolUseId || ""}
        questions={question?.questions || []}
        onAnswer={handleQuestionAnswer}
      />

      {showSettings && (
        <SessionSettings
          sessionId={selectedSessionId}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}
