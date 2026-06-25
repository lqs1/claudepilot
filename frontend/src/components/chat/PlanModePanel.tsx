import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";

import {
  Check,
  X,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Lightbulb,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { messageApi } from "@/api";

export interface PlanStep {
  id: string;
  text: string;
  status: "pending" | "active" | "completed" | "skipped";
}

export interface PlanState {
  sessionId: string;
  isActive: boolean;
  steps: PlanStep[];
  rawPlan: string;
}

interface PlanModePanelProps {
  plan: PlanState | null;
  onPlanChange?: (plan: PlanState | null) => void;
}

export function PlanModePanel({ plan, onPlanChange }: PlanModePanelProps) {
  const { t } = useTranslation();
  const [feedbackText, setFeedbackText] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  const handleApprove = useCallback(async () => {
    if (!plan?.sessionId) return;
    setIsSubmitting(true);
    try {
      await messageApi.planFeedback(plan.sessionId, "approve", "");
      onPlanChange?.(null);
    } catch (err) {
      console.error("Failed to approve plan", err);
    } finally {
      setIsSubmitting(false);
    }
  }, [plan?.sessionId, onPlanChange]);

  const handleReject = useCallback(async () => {
    if (!plan?.sessionId) return;
    setIsSubmitting(true);
    try {
      await messageApi.planFeedback(plan.sessionId, "reject", "");
      onPlanChange?.(null);
    } catch (err) {
      console.error("Failed to reject plan", err);
    } finally {
      setIsSubmitting(false);
    }
  }, [plan?.sessionId, onPlanChange]);

  const handleFeedback = useCallback(async () => {
    if (!plan?.sessionId || !feedbackText.trim()) return;
    setIsSubmitting(true);
    try {
      await messageApi.planFeedback(
        plan.sessionId,
        "feedback",
        feedbackText.trim(),
      );
      setFeedbackText("");
      setShowFeedback(false);
      onPlanChange?.(null);
    } catch (err) {
      console.error("Failed to send plan feedback", err);
    } finally {
      setIsSubmitting(false);
    }
  }, [plan?.sessionId, feedbackText, onPlanChange]);

  if (!plan || !plan.isActive) {
    return null;
  }

  const activeStep = plan.steps.find((s) => s.status === "active");

  return (
    <div className="border border-border rounded-lg bg-card shadow-sm overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 bg-muted/50 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <span className="text-sm font-medium">
            {t("plan.title") || "Plan Mode"}
          </span>
          {activeStep && (
            <span className="text-xs text-muted-foreground">
              {t("plan.step") || "Step"} {plan.steps.indexOf(activeStep) + 1}/
              {plan.steps.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {plan.steps.filter((s) => s.status === "completed").length}/
            {plan.steps.length}
          </span>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {isExpanded && (
        <>
          <div className="px-4 py-3 max-h-60 overflow-y-auto">
            {plan.steps.length === 0 ? (
              <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                {plan.rawPlan}
              </div>
            ) : (
              <ol className="space-y-2">
                {plan.steps.map((step, index) => (
                  <li
                    key={step.id}
                    className={`flex items-start gap-2 text-sm ${
                      step.status === "active"
                        ? "text-amber-600 dark:text-amber-400 font-medium"
                        : step.status === "completed"
                          ? "text-green-600 dark:text-green-400"
                          : step.status === "skipped"
                            ? "text-muted-foreground line-through"
                            : "text-foreground"
                    }`}
                  >
                    <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs mt-0.5">
                      {step.status === "completed" ? (
                        <Check className="h-3.5 w-3.5 text-green-500" />
                      ) : step.status === "skipped" ? (
                        <X className="h-3.5 w-3.5 text-muted-foreground" />
                      ) : step.status === "active" ? (
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                      ) : (
                        <span className="text-muted-foreground">
                          {index + 1}
                        </span>
                      )}
                    </span>
                    <span className="flex-1">{step.text}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <div className="px-4 py-3 border-t border-border bg-muted/30">
            {showFeedback ? (
              <div className="space-y-2">
                <Textarea
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder={
                    t("plan.feedbackPlaceholder") ||
                    "Enter your feedback on this plan..."
                  }
                  className="min-h-[80px] text-sm"
                  disabled={isSubmitting}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowFeedback(false);
                      setFeedbackText("");
                    }}
                    disabled={isSubmitting}
                  >
                    {t("common.cancel") || "Cancel"}
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleFeedback}
                    disabled={isSubmitting || !feedbackText.trim()}
                  >
                    {isSubmitting
                      ? t("common.sending") || "Sending..."
                      : t("plan.sendFeedback") || "Send Feedback"}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleApprove}
                  disabled={isSubmitting}
                  className="flex items-center gap-1"
                >
                  <Check className="h-3.5 w-3.5" />
                  {t("plan.approve") || "Approve"}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleReject}
                  disabled={isSubmitting}
                  className="flex items-center gap-1"
                >
                  <X className="h-3.5 w-3.5" />
                  {t("plan.reject") || "Reject"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFeedback(true)}
                  disabled={isSubmitting}
                  className="flex items-center gap-1"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  {t("plan.feedback") || "Feedback"}
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
