import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { presetApi, settingsApi } from "@/api";
import type { Preset } from "@/api";

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

// Suggestions only (datalist) — the model field is free text so new CLI
// models work without a code change. Do NOT hardcode a select (v2 §7).
const MODEL_SUGGESTIONS = [
  "claude-sonnet-4-20250514",
  "claude-opus-4",
  "claude-haiku-4",
];

// Effort choices mirror the live `claude --help` for --effort.
const EFFORT_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "xhigh", label: "XHigh" },
  { value: "max", label: "Max" },
];

// Permission modes mirror `claude --help` --permission-mode choices exactly.
const PERMISSION_OPTIONS = [
  { value: "default", label: "Default" },
  { value: "acceptEdits", label: "Accept Edits" },
  { value: "plan", label: "Plan" },
  { value: "auto", label: "Auto" },
  { value: "bypassPermissions", label: "Bypass Permissions" },
  { value: "dontAsk", label: "Don't Ask" },
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

  return { settings, setSettings, isLoading, updateField };
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
  const { settings, setSettings, isLoading, updateField } =
    useSessionSettings(sessionId);
  const { isSaving, save } = useSaveSettings(sessionId, onClose);
  const [presets, setPresets] = useState<Preset[]>([]);

  useEffect(() => {
    presetApi
      .list()
      .then((res) => setPresets(res.data.presets))
      .catch(() => {});
  }, []);

  const applyPreset = (presetId: string) => {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;
    setSettings({ ...DEFAULT_SETTINGS, ...preset.settings });
  };

  const saveAsPreset = async () => {
    const name = window.prompt(t("settings.presetNamePrompt"), "");
    if (!name?.trim()) return;
    try {
      const res = await presetApi.create(name.trim(), settings);
      setPresets((prev) => [...prev, res.data.preset]);
    } catch (err) {
      console.error("Failed to save preset", err);
      alert(err instanceof Error ? err.message : "Failed to save preset");
    }
  };

  const deletePreset = async (presetId: string) => {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;
    if (!window.confirm(t("settings.confirmDeletePreset"))) return;
    try {
      await presetApi.delete(presetId);
      setPresets((prev) => prev.filter((p) => p.id !== presetId));
    } catch (err) {
      console.error("Failed to delete preset", err);
    }
  };

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

        {/* Preset management: apply / save / delete */}
        <div className="mb-4 space-y-2 rounded-md border border-input bg-background p-3">
          <label className="block text-sm font-medium">
            {t("settings.presets")}
          </label>
          <div className="flex items-center gap-2">
            <select
              value=""
              onChange={(e) => e.target.value && applyPreset(e.target.value)}
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">
                {t("settings.selectPreset") || "— Select a preset —"}
              </option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={saveAsPreset}
              disabled={isLoading}
              title={t("settings.saveAsPreset")}
            >
              {t("settings.saveAsPreset")}
            </Button>
          </div>
          {presets.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {presets.map((p) => (
                <button
                  key={p.id}
                  onClick={() => deletePreset(p.id)}
                  className="group inline-flex items-center gap-1 rounded-full border border-input bg-background px-2.5 py-1 text-xs hover:border-destructive hover:text-destructive"
                  title={t("settings.deletePreset")}
                >
                  {p.name}
                  <span className="opacity-60 group-hover:opacity-100">×</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {t("settings.loading")}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">
                {t("settings.model")}
              </label>
              <input
                list="model-suggestions"
                value={settings.model}
                onChange={(e) => updateField("model", e.target.value)}
                placeholder={t("settings.model") || "model"}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <datalist id="model-suggestions">
                {MODEL_SUGGESTIONS.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
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
