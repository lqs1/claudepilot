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

export function parsePlanSteps(planText: string): PlanState["steps"] {
  const lines = planText.split("\n").filter((line) => line.trim());
  const steps: PlanState["steps"] = [];
  let stepIndex = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    const match = trimmed.match(/^(?:\d+[.):\s]+|Step\s+\d+[:\s]+)\s*(.+)$/i);
    if (match) {
      steps.push({
        id: `step-${stepIndex}`,
        text: match[1],
        status: "pending",
      });
      stepIndex++;
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      steps.push({
        id: `step-${stepIndex}`,
        text: trimmed.slice(2),
        status: "pending",
      });
      stepIndex++;
    }
  }

  return steps;
}

export function mergeSteps(
  existing: PlanState["steps"],
  incoming: PlanState["steps"],
): PlanState["steps"] {
  if (existing.length === 0) return incoming;
  if (incoming.length === 0) return existing;

  const merged: PlanState["steps"] = [];
  const maxLen = Math.max(existing.length, incoming.length);

  for (let i = 0; i < maxLen; i++) {
    if (i < incoming.length) {
      const existingStep = existing[i];
      merged.push({
        ...incoming[i],
        status:
          existingStep?.status === "completed"
            ? "completed"
            : incoming[i].status,
      });
    } else if (i < existing.length) {
      merged.push(existing[i]);
    }
  }

  return merged;
}
