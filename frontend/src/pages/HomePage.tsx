import { Plus, Terminal } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { ChatPage } from "@/pages/ChatPage";
import { FileBrowserPage } from "@/pages/FileBrowserPage";
import { QuickOpenDialog } from "@/components/editor/QuickOpenDialog";
import { XTermTerminal } from "@/components/terminal/XTermTerminal";
import { projectApi, sessionApi, shellApi } from "@/api";
import { useAppStore } from "@/stores/appStore";

type TabKey = "chat" | "files" | "terminal";

export function HomePage() {
  const { t, i18n } = useTranslation();
  const {
    projects,
    selectedProjectId,
    sessions,
    selectedSessionId,
    messages,
    language,
    setProjects,
    selectProject,
    setSessions,
    selectSession,
    setLanguage,
  } = useAppStore();

  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectPath, setNewProjectPath] = useState("");
  const [openPath, setOpenPath] = useState("");
  const [isQuickOpenOpen, setIsQuickOpenOpen] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState("");
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const [shellId, setShellId] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadSessions(selectedProjectId);
    }
  }, [selectedProjectId]);

  const loadProjects = async () => {
    try {
      const response = await projectApi.list();
      setProjects(response.data.projects);
    } catch (err) {
      console.error("Failed to load projects", err);
    }
  };

  const loadSessions = async (projectId: string) => {
    try {
      const response = await sessionApi.list(projectId);
      setSessions(response.data.sessions);
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName || !newProjectPath) return;
    try {
      await projectApi.create(newProjectName, newProjectPath);
      setNewProjectName("");
      setNewProjectPath("");
      await loadProjects();
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  const handleOpenProject = async () => {
    if (!openPath) return;
    try {
      const response = await projectApi.open(openPath);
      setOpenPath("");
      await loadProjects();
      selectProject(response.data.project.id);
    } catch (err) {
      console.error("Failed to open project", err);
      alert(err instanceof Error ? err.message : "Failed to open project");
    }
  };

  const handleCreateSession = async () => {
    if (!selectedProjectId || isCreatingSession) return;

    const title = newSessionTitle.trim() || t("chat.newSession");

    // Reuse an existing empty session instead of creating duplicates.
    const emptySession = sessions.find((session) => {
      const sessionMessages = messages[session.id];
      return !sessionMessages || sessionMessages.length === 0;
    });
    if (emptySession && title === t("chat.newSession")) {
      selectSession(emptySession.id);
      setNewSessionTitle("");
      return;
    }

    setIsCreatingSession(true);
    try {
      const response = await sessionApi.create(
        selectedProjectId,
        title,
        language,
      );
      setNewSessionTitle("");
      await loadSessions(selectedProjectId);
      selectSession(response.data.session.id);
    } catch (err) {
      console.error("Failed to create session", err);
    } finally {
      setIsCreatingSession(false);
    }
  };

  const toggleLanguage = () => {
    const next = language === "zh" ? "en" : "zh";
    setLanguage(next);
    i18n.changeLanguage(next);
  };

  const handleStartShell = async () => {
    try {
      const response = await shellApi.start();
      setShellId(response.data.shell_id);
    } catch (err) {
      console.error("Failed to start shell", err);
    }
  };

  const handleStopShell = async () => {
    if (!shellId) return;
    try {
      await shellApi.stop(shellId);
      setShellId(null);
    } catch (err) {
      console.error("Failed to stop shell", err);
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <div className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <h1 className="text-lg font-bold">{t("appName")}</h1>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {/* Projects */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                {t("project.title")}
              </span>
            </div>
            <div className="space-y-1">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => selectProject(project.id)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selectedProjectId === project.id
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted"
                  }`}
                >
                  {project.name}
                </button>
              ))}
            </div>

            <div className="space-y-2 pt-2">
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder={t("project.name")}
                className="w-full px-2 py-1 text-xs rounded border border-input bg-background"
              />
              <input
                type="text"
                value={newProjectPath}
                onChange={(e) => setNewProjectPath(e.target.value)}
                placeholder={t("project.path")}
                className="w-full px-2 py-1 text-xs rounded border border-input bg-background"
              />
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={handleCreateProject}
              >
                <Plus className="h-3 w-3 mr-1" /> {t("project.create")}
              </Button>
            </div>

            <div className="space-y-1 pt-3 border-t border-border">
              <span className="text-xs font-medium text-muted-foreground">
                {t("project.openLocal")}
              </span>
              <div className="flex gap-1">
                <input
                  type="text"
                  value={openPath}
                  onChange={(e) => setOpenPath(e.target.value)}
                  placeholder="/path/to/your/project"
                  className="flex-1 px-2 py-1 text-xs rounded border border-input bg-background"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsQuickOpenOpen(true)}
                >
                  {t("project.browse")}
                </Button>
              </div>
              <Button
                size="sm"
                variant="secondary"
                className="w-full"
                onClick={handleOpenProject}
              >
                {t("project.open")}
              </Button>
            </div>

            <QuickOpenDialog
              isOpen={isQuickOpenOpen}
              onClose={() => setIsQuickOpenOpen(false)}
              onSelect={(path) => setOpenPath(path)}
            />
          </div>

          {/* Sessions */}
          {selectedProjectId && (
            <div className="space-y-2 pt-4 border-t border-border">
              <span className="text-sm font-medium text-muted-foreground">
                {t("session.title")}
              </span>
              <div className="space-y-1">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => selectSession(session.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      selectedSessionId === session.id
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }`}
                  >
                    {session.title}
                  </button>
                ))}
              </div>
              <div className="space-y-1 pt-2">
                <input
                  type="text"
                  value={newSessionTitle}
                  onChange={(e) => setNewSessionTitle(e.target.value)}
                  placeholder={t("session.newSession")}
                  className="w-full px-2 py-1 text-xs rounded border border-input bg-background"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={handleCreateSession}
                  disabled={isCreatingSession}
                >
                  <Plus className="h-3 w-3 mr-1" /> {t("session.newSession")}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Language toggle */}
        <div className="p-4 border-t border-border">
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            onClick={toggleLanguage}
          >
            {language === "zh" ? t("settings.chinese") : t("settings.english")}
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedProjectId ? (
          <>
            <div className="flex items-center border-b border-border bg-card">
              {(["chat", "files", "terminal"] as TabKey[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 text-sm font-medium capitalize ${
                    activeTab === tab
                      ? "border-b-2 border-primary text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              {activeTab === "chat" && <ChatPage />}
              {activeTab === "files" && (
                <FileBrowserPage projectId={selectedProjectId} />
              )}
              {activeTab === "terminal" && (
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-card">
                    <span className="text-sm font-medium flex items-center gap-2">
                      <Terminal className="h-4 w-4" />
                      {shellId ? `Shell: ${shellId}` : "No shell running"}
                    </span>
                    <div className="flex items-center gap-2">
                      {shellId ? (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={handleStopShell}
                        >
                          Stop
                        </Button>
                      ) : (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={handleStartShell}
                        >
                          Start Shell
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    {shellId ? (
                      <XTermTerminal shellId={shellId} />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                        Click "Start Shell" to open a terminal
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
            Select or create a project to start
          </div>
        )}
      </div>
    </div>
  );
}
