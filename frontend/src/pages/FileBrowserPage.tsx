import { useState } from "react";

import { FileTree } from "@/components/editor/FileTree";
import { MonacoFileEditor } from "@/components/editor/MonacoFileEditor";
import type { FileEntry } from "@/api";

interface FileBrowserPageProps {
  projectId: string;
}

export function FileBrowserPage({ projectId }: FileBrowserPageProps) {
  const [selectedFile, setSelectedFile] = useState<FileEntry | null>(null);

  const handleSelect = (entry: FileEntry) => {
    if (entry.type === "file") {
      setSelectedFile(entry);
    }
  };

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-border bg-card overflow-y-auto">
        <FileTree
          projectId={projectId}
          onSelect={handleSelect}
          selectedPath={selectedFile?.path}
        />
      </div>
      <div className="flex-1 min-w-0">
        <MonacoFileEditor
          projectId={projectId}
          path={selectedFile?.path || ""}
        />
      </div>
    </div>
  );
}
