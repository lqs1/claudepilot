import { ChevronRight, File, Folder, FolderOpen } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { filesystemApi, type FileEntry } from "@/api";

interface FileTreeProps {
  projectId: string;
  onSelect: (entry: FileEntry) => void;
  selectedPath?: string;
}

interface TreeNode {
  entry: FileEntry;
  children?: TreeNode[];
  isExpanded: boolean;
  isLoading: boolean;
}

export function FileTree({ projectId, onSelect, selectedPath }: FileTreeProps) {
  const [root, setRoot] = useState<TreeNode[]>([]);
  const [error, setError] = useState<string | null>(null);

  const updateNodes = useCallback((path: string, entries: FileEntry[]) => {
    setRoot((prev) => {
      if (path === "") {
        return entries.map((entry) => ({
          entry,
          children: entry.type === "directory" ? [] : undefined,
          isExpanded: false,
          isLoading: false,
        }));
      }
      return updateNodeChildren(prev, path, entries);
    });
  }, []);

  const loadDirectory = useCallback(
    async (path: string) => {
      try {
        const response = await filesystemApi.browse(projectId, path);
        updateNodes(path, response.data.entries);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load directory",
        );
      }
    },
    [projectId, updateNodes],
  );

  useEffect(() => {
    loadDirectory("");
  }, [projectId, loadDirectory]);

  const updateNodeChildren = (
    nodes: TreeNode[],
    targetPath: string,
    entries: FileEntry[],
  ): TreeNode[] => {
    return nodes.map((node) => {
      if (node.entry.path === targetPath) {
        return {
          ...node,
          isLoading: false,
          children: entries.map((entry) => ({
            entry,
            children: entry.type === "directory" ? [] : undefined,
            isExpanded: false,
            isLoading: false,
          })),
        };
      }
      if (node.children) {
        return {
          ...node,
          children: updateNodeChildren(node.children, targetPath, entries),
        };
      }
      return node;
    });
  };

  const toggleDirectory = (node: TreeNode) => {
    if (node.entry.type !== "directory") return;

    if (node.isExpanded) {
      collapseNode(node.entry.path);
      return;
    }

    setRoot((prev) => setExpanded(prev, node.entry.path, true, true));
    loadDirectory(node.entry.path);
  };

  const collapseNode = (targetPath: string) => {
    setRoot((prev) => setExpanded(prev, targetPath, false, false));
  };

  const setExpanded = (
    nodes: TreeNode[],
    targetPath: string,
    expanded: boolean,
    loading: boolean,
  ): TreeNode[] => {
    return nodes.map((node) => {
      if (node.entry.path === targetPath) {
        return { ...node, isExpanded: expanded, isLoading: loading };
      }
      if (node.children) {
        return {
          ...node,
          children: setExpanded(node.children, targetPath, expanded, loading),
        };
      }
      return node;
    });
  };

  const handleSelect = (node: TreeNode) => {
    if (node.entry.type === "directory") {
      toggleDirectory(node);
    } else {
      onSelect(node.entry);
    }
  };

  const renderNode = (node: TreeNode, depth: number = 0) => {
    const isSelected = node.entry.path === selectedPath;
    const paddingLeft = `${depth * 16 + 8}px`;

    return (
      <div key={node.entry.path}>
        <button
          onClick={() => handleSelect(node)}
          className={`flex w-full items-center gap-1 rounded-lg px-2 py-1 text-left text-sm text-foreground transition-colors ${
            isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted/50"
          }`}
          style={{ paddingLeft }}
        >
          {node.entry.type === "directory" && (
            <ChevronRight
              className={`h-3 w-3 shrink-0 text-muted-foreground transition-transform ${node.isExpanded ? "rotate-90" : ""}`}
            />
          )}
          {node.entry.type === "directory" ? (
            node.isExpanded ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-yellow-500" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-yellow-500" />
            )
          ) : (
            <File className="h-4 w-4 shrink-0 text-primary" />
          )}
          <span className="truncate">{node.entry.name}</span>
        </button>
        {node.isExpanded && node.children && (
          <div>
            {node.isLoading ? (
              <div className="px-4 py-1 text-xs text-muted-foreground">
                Loading...
              </div>
            ) : (
              node.children.map((child) => renderNode(child, depth + 1))
            )}
          </div>
        )}
      </div>
    );
  };

  if (error) {
    return <div className="p-2 text-sm text-destructive">{error}</div>;
  }

  return <div className="py-1">{root.map((node) => renderNode(node))}</div>;
}
