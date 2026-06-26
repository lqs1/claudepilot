import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { FileEdit, FilePlus } from "lucide-react";

import { DiffView } from "@/components/changes/DiffView";
import { messageApi } from "@/api";
import type { ChangeEntry } from "@/api";

interface ChangesPageProps {
  sessionId: string | null;
}

// Group changes by file, preserving order within each file.
interface FileGroup {
  path: string;
  changes: ChangeEntry[];
}

export function ChangesPage({ sessionId }: ChangesPageProps) {
  const { t } = useTranslation();
  const [changes, setChanges] = useState<ChangeEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setChanges([]);
      return;
    }
    setIsLoading(true);
    messageApi
      .getChanges(sessionId)
      .then((res) => setChanges(res.data.changes))
      .catch(() => setChanges([]))
      .finally(() => setIsLoading(false));
  }, [sessionId]);

  const groups: FileGroup[] = useMemo(() => {
    const map = new Map<string, ChangeEntry[]>();
    for (const c of changes) {
      const list = map.get(c.file_path);
      if (list) list.push(c);
      else map.set(c.file_path, [c]);
    }
    // Preserve first-appearance order across files.
    return Array.from(map.entries()).map(([path, list]) => ({
      path,
      changes: list,
    }));
  }, [changes]);

  // Auto-select first file when groups change.
  useEffect(() => {
    if (groups.length && !groups.some((g) => g.path === selectedPath)) {
      setSelectedPath(groups[0].path);
    }
  }, [groups, selectedPath]);

  const selected = groups.find((g) => g.path === selectedPath);

  if (!sessionId) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        {t("session.newSession")}
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* File list */}
      <div className="w-64 border-r border-border bg-card overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-xs text-muted-foreground">
            {t("settings.loading")}
          </div>
        ) : groups.length === 0 ? (
          <div className="p-4 text-xs text-muted-foreground">
            {t("changes.empty") || "No file changes in this session yet."}
          </div>
        ) : (
          <ul className="py-1">
            {groups.map((g) => {
              const created = g.changes.some((c) => c.kind === "create");
              return (
                <li key={g.path}>
                  <button
                    onClick={() => setSelectedPath(g.path)}
                    className={`group flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors ${
                      selectedPath === g.path
                        ? "bg-primary/10 text-foreground"
                        : "hover:bg-muted/40 text-foreground/80"
                    }`}
                    title={g.path}
                  >
                    {created ? (
                      <FilePlus className="h-3.5 w-3.5 flex-shrink-0 text-green-500" />
                    ) : (
                      <FileEdit className="h-3.5 w-3.5 flex-shrink-0 text-amber-500" />
                    )}
                    <span className="truncate">{fileName(g.path)}</span>
                    {g.changes.length > 1 && (
                      <span className="ml-auto rounded-full bg-muted px-1.5 text-[10px] text-muted-foreground">
                        {g.changes.length}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Diff detail */}
      <div className="flex-1 min-w-0 overflow-y-auto p-4 space-y-3">
        {selected ? (
          <>
            <div className="text-xs text-muted-foreground font-mono break-all">
              {selected.path}
            </div>
            {selected.changes.map((c) => (
              <DiffView key={`${c.turn_uuid}-${c.order}`} change={c} />
            ))}
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            {t("changes.empty") || "No file changes in this session yet."}
          </div>
        )}
      </div>
    </div>
  );
}

function fileName(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}
