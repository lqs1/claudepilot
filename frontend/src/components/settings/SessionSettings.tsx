import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { settingsApi } from "@/api";

interface SessionSettingsData {
  model: string;
  effort: string;
  permission_mode: string;
  tools_enabled: boolean;
  max_turns: number | undefined;
}

const DEFAULT_SETTINGS: SessionSettingsData = {
  model: "claude-sonnet-4-20250514",
  effort: "medium",
  permission_mode: "acceptEdits",
  tools_enabled: true,
  max_turns: undefined,
};

const MODEL_OPTIONS = [
  { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
  { value: "claude-opus-4", label: "Claude Opus 4" },
  { value: "claude-haiku-4", label: "Claude Haiku 4" },
];

const EFFORT_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "xhigh", label: "XHigh" },
  { value: "max", label: "Max" },
];

const PERMISSION_OPTIONS = [
  { value: "acceptEdits", label: "Accept Edits" },
  { value: "acceptAll", label: "Accept All" },
  { value: "rejectAll", label: "Reject All" },
  { value: "askUser", label: "Ask User" },
];

interface SessionSettingsProps {
  sessionId: string | null;
  onClose: () => void;
}

function useSessionSettings(sessionId: string | null) {
  const [settings, setSettings] =
    useState<SessionSettingsData>(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    setIsLoading(true);
    settingsApi
      .getSession(sessionId)
      .then((res) => {
        setSettings({ ...DEFAULT_SETTINGS, ...res.data.settings });
      })
      .catch(() => {
        // Fall back to defaults on error
      })
      .finally(() => setIsLoading(false));
  }, [sessionId]);

  const updateField = <K extends keyof SessionSettingsData>(
    key: K,
    value: SessionSettingsData[K],
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return { settings, isLoading, updateField };
}

function useSaveSettings(sessionId: string | null, onClose: () => void) {
  const [isSaving, setIsSaving] = useState(false);

  const save = async (settings: SessionSettingsData, applyGlobal = false) => {
    if (!sessionId) return;
    setIsSaving(true);
    try {
      await settingsApi.updateSession(sessionId, settings);
      if (applyGlobal) {
        await settingsApi.updateGlobal(settings);
      }
      onClose();
    } catch (err) {
      console.error("Failed to save settings", err);
    } finally {
      setIsSaving(false);
    }
  };

  return { isSaving, save };
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  placeholder,
  onChange,
}: {
  label: string;
  value: number | undefined;
  min?: number;
  max?: number;
  placeholder?: string;
  onChange: (value: number | undefined) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      <input
        type="number"
        min={min}
        max={max}
        placeholder={placeholder}
        value={value ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(undefined);
            return;
          }
          const parsed = parseInt(raw, 10);
          onChange(Number.isNaN(parsed) ? undefined : parsed);
        }}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function ToggleField({
  label,
  enabled,
  onToggle,
}: {
  label: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-input bg-background px-3 py-2">
      <label className="text-sm font-medium">{label}</label>
      <button
        onClick={onToggle}
        className={`relative h-5 w-9 rounded-full transition-colors ${
          enabled ? "bg-primary" : "bg-muted"
        }`}
        aria-label="Toggle"
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
            enabled ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export function SessionSettings({ sessionId, onClose }: SessionSettingsProps) {
  const { t } = useTranslation();
  const { settings, isLoading, updateField } = useSessionSettings(sessionId);
  const { isSaving, save } = useSaveSettings(sessionId, onClose);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {t("settings.sessionTitle")}
          </h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close"
          >
            <CloseIcon />
          </button>
        </div>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {t("settings.loading")}
          </div>
        ) : (
          <div className="space-y-4">
            <SelectField
              label={t("settings.model")}
              value={settings.model}
              options={MODEL_OPTIONS}
              onChange={(v) => updateField("model", v)}
            />
            <SelectField
              label={t("settings.effort")}
              value={settings.effort}
              options={EFFORT_OPTIONS}
              onChange={(v) => updateField("effort", v)}
            />
            <SelectField
              label={t("settings.permissionMode")}
              value={settings.permission_mode}
              options={PERMISSION_OPTIONS}
              onChange={(v) => updateField("permission_mode", v)}
            />
            <NumberField
              label={t("settings.maxTurns")}
              value={settings.max_turns}
              min={1}
              placeholder={t("settings.unlimited") || "Unlimited"}
              onChange={(v) => updateField("max_turns", v)}
            />
            <ToggleField
              label={t("settings.toolsEnabled")}
              enabled={settings.tools_enabled}
              onToggle={() =>
                updateField("tools_enabled", !settings.tools_enabled)
              }
            />
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {t("settings.cancel")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => save(settings, true)}
            disabled={isSaving || isLoading}
          >
            {isSaving ? t("settings.saving") : t("settings.saveAsGlobal")}
          </Button>
          <Button
            size="sm"
            onClick={() => save(settings, false)}
            disabled={isSaving || isLoading}
          >
            {isSaving ? t("settings.saving") : t("settings.save")}
          </Button>
        </div>
      </div>
    </div>
  );
}
