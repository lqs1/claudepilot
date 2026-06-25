import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

import { Button } from "@/components/ui/button";
import { filesystemApi } from "@/api";

interface MonacoFileEditorProps {
  projectId: string;
  path: string;
}

export function MonacoFileEditor({ projectId, path }: MonacoFileEditorProps) {
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setContent("");
      setOriginalContent("");
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    filesystemApi
      .read(projectId, path)
      .then((response) => {
        if (cancelled) return;
        setContent(response.data.content);
        setOriginalContent(response.data.content);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to read file");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, path]);

  const handleSave = async () => {
    if (!path) return;
    setIsSaving(true);
    try {
      await filesystemApi.write(projectId, path, content);
      setOriginalContent(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save file");
    } finally {
      setIsSaving(false);
    }
  };

  const isDirty = content !== originalContent;

  if (!path) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Select a file to edit
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <span className="text-sm font-medium truncate">{path}</span>
        <Button size="sm" onClick={handleSave} disabled={!isDirty || isSaving}>
          {isSaving ? "Saving..." : "Save"}
        </Button>
      </div>
      {error && (
        <div className="text-sm text-destructive px-4 py-2 border-b border-border">
          {error}
        </div>
      )}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language={detectLanguage(path)}
          value={content}
          onChange={(value: string | undefined) => setContent(value || "")}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: "on",
          }}
        />
      </div>
    </div>
  );
}

function detectLanguage(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase();
  const map: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    tsx: "typescript",
    jsx: "javascript",
    json: "json",
    md: "markdown",
    html: "html",
    css: "css",
    yaml: "yaml",
    yml: "yaml",
    sh: "shell",
    go: "go",
    rs: "rust",
    java: "java",
    c: "c",
    cpp: "cpp",
    h: "cpp",
  };
  return map[ext || ""] || "plaintext";
}
