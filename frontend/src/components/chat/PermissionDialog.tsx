import { ShieldCheck, ShieldX } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PermissionDialogProps {
  isOpen: boolean;
  sessionId: string;
  toolUseId: string;
  tool: string;
  operation: string;
  reason: string;
  onRespond: (sessionId: string, toolUseId: string, allowed: boolean) => void;
}

export function PermissionDialog({
  isOpen,
  sessionId,
  toolUseId,
  tool,
  operation,
  reason,
  onRespond,
}: PermissionDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-[480px] max-w-[90vw] bg-background border border-border rounded-lg shadow-lg">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-yellow-500" />
          <span className="font-medium">Permission Request</span>
        </div>

        <div className="px-4 py-4 space-y-3">
          <div>
            <span className="text-xs text-muted-foreground">Tool</span>
            <div className="text-sm font-mono">{tool}</div>
          </div>
          {operation && (
            <div>
              <span className="text-xs text-muted-foreground">Operation</span>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-[200px]">
                {operation}
              </pre>
            </div>
          )}
          {reason && (
            <div>
              <span className="text-xs text-muted-foreground">Reason</span>
              <div className="text-sm">{reason}</div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRespond(sessionId, toolUseId, false)}
          >
            <ShieldX className="h-4 w-4 mr-1" /> Deny
          </Button>
          <Button
            size="sm"
            onClick={() => onRespond(sessionId, toolUseId, true)}
          >
            <ShieldCheck className="h-4 w-4 mr-1" /> Allow
          </Button>
        </div>
      </div>
    </div>
  );
}
