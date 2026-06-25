import { HelpCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

interface QuestionItem {
  question: string;
  header?: string;
  options: Array<{ value: string; label?: string }>;
  multi_select?: boolean;
}

interface QuestionDialogProps {
  isOpen: boolean;
  sessionId: string;
  toolUseId: string;
  questions: QuestionItem[];
  onAnswer: (
    sessionId: string,
    toolUseId: string,
    answers: Array<Record<string, unknown>>,
  ) => void;
}

export function QuestionDialog({
  isOpen,
  sessionId,
  toolUseId,
  questions,
  onAnswer,
}: QuestionDialogProps) {
  const [selections, setSelections] = useState<Record<number, string[]>>({});

  if (!isOpen) return null;

  const toggleOption = (qIndex: number, value: string) => {
    setSelections((prev) => {
      const current = prev[qIndex] || [];
      const updated = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value];
      return { ...prev, [qIndex]: updated };
    });
  };

  const handleSubmit = () => {
    const answers = questions.map((q, i) => ({
      question: q.question,
      options: (selections[i] || []).map((v) => ({ value: v })),
    }));
    onAnswer(sessionId, toolUseId, answers);
    setSelections({});
  };

  const allAnswered = questions.every(
    (_, i) => (selections[i] || []).length > 0,
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-[520px] max-w-[90vw] bg-background border border-border rounded-lg shadow-lg max-h-[80vh] flex flex-col">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2">
          <HelpCircle className="h-5 w-5 text-blue-500" />
          <span className="font-medium">Claude needs your input</span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {questions.map((q, qIndex) => (
            <div key={qIndex} className="space-y-2">
              {q.header && (
                <div className="text-xs font-medium text-muted-foreground">
                  {q.header}
                </div>
              )}
              <div className="text-sm">{q.question}</div>
              <div className="space-y-1">
                {q.options.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => toggleOption(qIndex, opt.value)}
                    className={`w-full text-left px-3 py-2 text-sm rounded border transition-colors ${
                      (selections[qIndex] || []).includes(opt.value)
                        ? "bg-primary text-primary-foreground border-primary"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    {opt.label || opt.value}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-end px-4 py-3 border-t border-border">
          <Button size="sm" onClick={handleSubmit} disabled={!allAnswered}>
            Submit
          </Button>
        </div>
      </div>
    </div>
  );
}
