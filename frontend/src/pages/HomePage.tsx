import { Plus, Terminal } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { NuminaInput } from "@/components/ui/numina-input";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { ChatPage } from "@/pages/ChatPage";
import { ChangesPage } from "@/pages/ChangesPage";
import { FileBrowserPage } from "@/pages/FileBrowserPage";
import { QuickOpenDialog } from "@/components/editor/QuickOpenDialog";
import { XTermTerminal } from "@/components/terminal/XTermTerminal";
import { projectApi, sessionApi, shellApi } from "@/api";
import { useAppStore } from "@/stores/appStore";

type TabKey = "chat" | "files" | "terminal" | "changes";

function SidebarNavItem({
  active,
  loading,
  onClick,
  children,
}: {
  active: boolean;
  loading?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`group relative w-full rounded-xl px-3 py-2 text-left text-sm transition-all duration-200 ${
        active
          ? "bg-sidebar-active text-sidebar-fg tech-glow"
          : "text-sidebar-fg hover:bg-sidebar-hover"
      }`}
    >
      {active && !loading && (
        <span className="absolute left-0 top-1/2 h-[60%] w-[3px] -translate-y-1/2 rounded-r bg-gradient-to-b from-transparent via-primary to-transparent" />
      )}
      {/* Animated rainbow left bar while the session is busy. */}
      {loading && (
        <span className="rainbow-flow rainbow-bar absolute left-0 top-0 h-full w-[3px] rounded-r" />
      )}
      <span className="relative z-10">{children}</span>
      {loading && <RainbowProgress />}
    </button>
  );
}

/** A thin flowing rainbow bar pinned along the bottom of a loading item. */
function RainbowProgress() {
  return (
    <span className="pointer-events-none absolute bottom-0 left-0 h-[2px] w-full overflow-hidden rounded-b">
      <span className="rainbow-flow block h-full w-full" />
    </span>
  );
}

export function HomePage() {
  const { t, i18n } = useTranslation();
  const {
    projects,
    selectedProjectId,
    sessions,
    selectedSessionId,
    messages,
    language,
    shellId,
    loadingSessionId,
    setProjects,
    selectProject,
    setSessions,
    selectSession,
    setLanguage,
    setShellId,
  } = useAppStore();

  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectPath, setNewProjectPath] = useState("");
  const [openPath, setOpenPath] = useState("");
  const [isQuickOpenOpen, setIsQuickOpenOpen] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState("");
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("chat");

  useEffect(() => {
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadSessions(selectedProjectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    <div className="flex h-screen bg-background text-foreground tech-bg-particles">
      {/* Sidebar */}
      <div className="w-64 flex flex-col bg-sidebar-bg text-sidebar-fg shadow-sidebar-raised">
        <div className="p-4">
          <h1 className="text-lg font-bold tracking-tight text-sidebar-fg">
            {t("appName")}
          </h1>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
          {/* Projects */}
          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-sidebar-muted">
                {t("project.title")}
              </span>
            </div>
            <div className="space-y-1">
              {projects.map((project) => (
                <SidebarNavItem
                  key={project.id}
                  active={selectedProjectId === project.id}
                  onClick={() => selectProject(project.id)}
                >
                  {project.name}
                </SidebarNavItem>
              ))}
            </div>

            <div className="space-y-2 rounded-xl p-3">
              <NuminaInput
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder={t("project.name")}
                className="text-xs"
              />
              <NuminaInput
                type="text"
                value={newProjectPath}
                onChange={(e) => setNewProjectPath(e.target.value)}
                placeholder={t("project.path")}
                className="text-xs"
              />
              <Button
                size="sm"
                variant="outline"
                className="w-full rounded-xl border-sidebar-hover bg-sidebar-hover text-sidebar-fg hover:bg-sidebar-active hover:text-sidebar-fg"
                onClick={handleCreateProject}
              >
                <Plus className="mr-1 h-3 w-3" /> {t("project.create")}
              </Button>
            </div>

            <div className="space-y-2 rounded-xl p-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-sidebar-muted">
                {t("project.openLocal")}
              </span>
              <div className="flex gap-2">
                <NuminaInput
                  type="text"
                  value={openPath}
                  onChange={(e) => setOpenPath(e.target.value)}
                  placeholder="/path/to/your/project"
                  className="flex-1 text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl border-sidebar-hover bg-sidebar-hover text-sidebar-fg hover:bg-sidebar-active hover:text-sidebar-fg"
                  onClick={() => setIsQuickOpenOpen(true)}
                >
                  {t("project.browse")}
                </Button>
              </div>
              <Button
                size="sm"
                variant="secondary"
                className="w-full rounded-xl"
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
            <div className="space-y-2">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-sidebar-muted">
                  {t("session.title")}
                </span>
              </div>
              <div className="space-y-1">
                {sessions.map((session) => (
                  <SidebarNavItem
                    key={session.id}
                    active={selectedSessionId === session.id}
                    loading={loadingSessionId === session.id}
                    onClick={() => selectSession(session.id)}
                  >
                    {session.title}
                  </SidebarNavItem>
                ))}
              </div>
              <div className="space-y-2 rounded-xl p-3">
                <NuminaInput
                  type="text"
                  value={newSessionTitle}
                  onChange={(e) => setNewSessionTitle(e.target.value)}
                  placeholder={t("session.newSession")}
                  className="text-xs"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full rounded-xl border-sidebar-hover bg-sidebar-hover text-sidebar-fg hover:bg-sidebar-active hover:text-sidebar-fg"
                  onClick={handleCreateSession}
                  disabled={isCreatingSession}
                >
                  <Plus className="mr-1 h-3 w-3" /> {t("session.newSession")}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Language toggle */}
        <div className="space-y-2 p-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-full rounded-xl text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-fg"
            onClick={toggleLanguage}
          >
            {language === "zh" ? t("settings.chinese") : t("settings.english")}
          </Button>
          <ThemeToggle />
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
        {selectedProjectId ? (
          <>
            <div
              className="flex items-center border-b border-transparent p-2"
              style={{ boxShadow: "var(--neu-raised-sm)" }}
            >
              {(["chat", "changes", "files", "terminal"] as TabKey[]).map(
                (tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-xl px-4 py-2 text-sm font-medium capitalize transition-all ${
                      activeTab === tab
                        ? "bg-primary text-primary-foreground shadow-neu-sm tech-btn-shimmer"
                        : "text-muted-foreground hover:bg-card hover:text-foreground"
                    }`}
                  >
                    {tab}
                  </button>
                ),
              )}
            </div>
            <div className="flex-1 overflow-hidden p-4">
              <div
                className="h-full overflow-hidden rounded-xl bg-card"
                style={{ boxShadow: "var(--neu-raised)" }}
                hidden={activeTab !== "chat"}
              >
                <ChatPage />
              </div>
              <div
                className="h-full overflow-hidden rounded-xl bg-card"
                style={{ boxShadow: "var(--neu-raised)" }}
                hidden={activeTab !== "changes"}
              >
                <ChangesPage sessionId={selectedSessionId} />
              </div>
              <div
                className="h-full overflow-hidden rounded-xl bg-card"
                style={{ boxShadow: "var(--neu-raised)" }}
                hidden={activeTab !== "files"}
              >
                <FileBrowserPage projectId={selectedProjectId} />
              </div>
              <div
                className="flex h-full flex-col overflow-hidden rounded-xl bg-card"
                style={{ boxShadow: "var(--neu-raised)" }}
                hidden={activeTab !== "terminal"}
              >
                <div
                  className="flex items-center justify-between px-4 py-3"
                  style={{ boxShadow: "var(--neu-raised-sm)" }}
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
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
                <div className="flex-1 overflow-hidden p-2">
                  {shellId ? (
                    <XTermTerminal
                      shellId={shellId}
                      hidden={activeTab !== "terminal"}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                      Click "Start Shell" to open a terminal
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Select or create a project to start
          </div>
        )}
      </div>
    </div>
  );
}
