import { ChevronRight, File, Folder, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { filesystemApi, type FileEntry } from "@/api";

interface QuickOpenDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
}

export function QuickOpenDialog({
  isOpen,
  onClose,
  onSelect,
}: QuickOpenDialogProps) {
  const [currentPath, setCurrentPath] = useState("");
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    loadHome();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const loadHome = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const homeResponse = await filesystemApi.home();
      const homePath = homeResponse.data.path;
      setCurrentPath(homePath);
      await loadDirectory(homePath);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load home directory",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const loadDirectory = async (path: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await filesystemApi.browseAbsolute(path);
      setCurrentPath(response.data.current_path);
      setEntries(response.data.entries);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to browse directory",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleEntryClick = (entry: FileEntry) => {
    if (entry.type === "directory") {
      loadDirectory(entry.path);
    }
  };

  const handleSelect = () => {
    if (currentPath) {
      onSelect(currentPath);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="flex max-h-[80vh] w-[600px] max-w-[90vw] flex-col rounded-xl bg-card shadow-neu">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="font-medium text-foreground">
            Select Local Directory
          </span>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="bg-muted/30 px-4 py-2">
          <div className="truncate text-xs text-muted-foreground">
            {currentPath}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="p-4 text-sm text-muted-foreground">Loading...</div>
          ) : error ? (
            <div className="p-4 text-sm text-destructive">{error}</div>
          ) : (
            <div className="space-y-1">
              {currentPath !== "/" && (
                <button
                  onClick={() => {
                    const parent =
                      currentPath.split("/").slice(0, -1).join("/") || "/";
                    loadDirectory(parent);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-foreground hover:bg-muted/50"
                >
                  <ChevronRight className="h-4 w-4 rotate-[-90deg] text-muted-foreground" />
                  <span>..</span>
                </button>
              )}
              {entries.map((entry) => (
                <button
                  key={entry.path}
                  onClick={() => handleEntryClick(entry)}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-foreground hover:bg-muted/50"
                >
                  {entry.type === "directory" ? (
                    <Folder className="h-4 w-4 text-yellow-500" />
                  ) : (
                    <File className="h-4 w-4 text-primary" />
                  )}
                  <span>{entry.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleSelect} disabled={!currentPath}>
            Select This Folder
          </Button>
        </div>
      </div>
    </div>
  );
}
