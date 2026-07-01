import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { presetApi, sessionApi } from "@/api";
import type { Preset } from "@/api";

interface BroadcastDialogProps {
  projectId: string;
  /** Initial prompt seed (e.g. the text currently in the chat input). */
  initialPrompt?: string;
  language: "zh" | "en";
  onDone: () => void;
}

/** Broadcast one prompt to one session per selected preset, in parallel. */
export function BroadcastDialog({
  projectId,
  initialPrompt,
  language,
  onDone,
}: BroadcastDialogProps) {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState(initialPrompt || "");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    presetApi
      .list()
      .then((res) => setPresets(res.data.presets))
      .catch(() => {});
  }, []);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBroadcast = async () => {
    if (!prompt.trim() || selected.size === 0) return;
    setSending(true);
    setError(null);
    try {
      const configurations = Array.from(selected).map((preset_id) => ({
        preset_id,
      }));
      // The terminal will refresh the session list after onDone; the broadcast
      // endpoint itself creates + starts all sessions server-side.
      await sessionApi.broadcast(
        projectId,
        prompt.trim(),
        configurations,
        language,
      );
      onDone();
    } catch (err) {
      console.error("Broadcast failed", err);
      setError(err instanceof Error ? err.message : "Broadcast failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {t("broadcast.title") || "并行广播"}
          </h2>
          <button
            onClick={onDone}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={t("chat.inputPlaceholder")}
          rows={3}
          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm"
        />

        <div className="mt-4">
          <div className="mb-2 text-sm font-medium">
            {t("broadcast.selectPresets") ||
              "选择预设（每个预设开一个并行会话）"}
          </div>
          {presets.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {t("broadcast.noPresets") ||
                "还没有预设。先在某个会话的设置里用「存为预设」创建。"}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => {
                const on = selected.has(p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => toggle(p.id)}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      on
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-input bg-background text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {p.name}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {error && <p className="mt-3 text-xs text-red-500">{error}</p>}

        <div className="mt-6 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {selected.size > 0
              ? `${t("broadcast.willStart") || "将启动"} ${selected.size} ${
                  selected.size === 1 ? "会话" : "个并行会话"
                }`
              : ""}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onDone}>
              {t("settings.cancel") || "取消"}
            </Button>
            <Button
              size="sm"
              onClick={handleBroadcast}
              disabled={sending || !prompt.trim() || selected.size === 0}
            >
              <Send className="mr-1 h-3.5 w-3.5" />
              {sending
                ? t("settings.saving")
                : `${t("settings.send") || "发送"} (${selected.size})`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
