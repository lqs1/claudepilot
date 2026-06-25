import { useEffect, useState, useCallback, useRef } from "react";
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
  const { selectedSessionId, messages, addMessage, setMessages, language } =
    useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [permission, setPermission] = useState<PermissionState | null>(null);
  const [question, setQuestion] = useState<QuestionState | null>(null);
  const [plan, setPlan] = useState<PlanState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

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

  const { subscribe, unsubscribe } = useWebSocket(wsHandler);
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

  // Check session status on mount / when session changes
  useEffect(() => {
    if (!selectedSessionId) {
      setIsRunning(false);
      return;
    }
    // Check if session already has messages from a running session
    const hasAssistantMessages = sessionMessages.some(
      (m) => m.role === "assistant",
    );
    if (hasAssistantMessages) {
      setIsRunning(true);
    }
  }, [selectedSessionId, sessionMessages]);

  useEffect(() => {
    if (!selectedSessionId) return;

    subscribe(selectedSessionId);
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
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card">
        <div className="text-sm font-medium">
          {t("session.title")} · {language.toUpperCase()}
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

      <MessageList messages={sessionMessages} isLoading={isLoading} />
      <PlanModePanel plan={plan} onPlanChange={setPlan} />
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
