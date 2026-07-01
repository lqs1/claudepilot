import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Project {
  id: string;
  name: string;
  path: string;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  project_id: string;
  title: string;
  language: "zh" | "en";
  status: string;
  started_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  uuid?: string;
  session_id: string;
  role: string;
  type: string;
  content: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  tool_status?: string;
  tool_uses?: Array<{
    id: string;
    name: string;
    input: Record<string, unknown>;
  }>;
  created_at: string;
}

export const projectApi = {
  list: () => api.get<{ projects: Project[] }>("/projects"),
  create: (name: string, path: string) =>
    api.post<{ project: Project }>("/projects", { name, path }),
  open: (path: string) =>
    api.post<{ project: Project }>("/projects/open", { path }),
  delete: (id: string) => api.delete<{ deleted: boolean }>(`/projects/${id}`),
};

export const sessionApi = {
  list: (projectId: string) =>
    api.get<{ sessions: Session[] }>(`/projects/${projectId}/sessions`),
  create: (projectId: string, title: string, language: "zh" | "en") =>
    api.post<{ session: Session }>(`/projects/${projectId}/sessions`, {
      title,
      language,
    }),
  broadcast: (
    projectId: string,
    prompt: string,
    configurations: Array<{ preset_id?: string; title?: string }>,
    language: "zh" | "en" = "zh",
  ) =>
    api.post<{ sessions: Session[] }>(
      `/projects/${projectId}/sessions/broadcast`,
      { prompt, configurations, language },
    ),
};

export const messageApi = {
  list: (sessionId: string) =>
    api.get<{ messages: Message[] }>(`/sessions/${sessionId}/messages`),
  send: (sessionId: string, content: string) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/messages`, {
      content,
    }),
  start: (sessionId: string) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/start`),
  stop: (sessionId: string) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/stop`),
  resume: (sessionId: string) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/resume`),
  answer: (
    sessionId: string,
    toolUseId: string,
    answers: Array<Record<string, unknown>>,
  ) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/answer`, {
      tool_use_id: toolUseId,
      answers,
    }),
  respondPermission: (sessionId: string, toolUseId: string, allowed: boolean) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/permission`, {
      tool_use_id: toolUseId,
      allowed,
    }),
  planFeedback: (sessionId: string, action: string, message: string) =>
    api.post<{ status: string }>(`/sessions/${sessionId}/plan-feedback`, {
      action,
      message,
    }),
  deleteTurn: (sessionId: string, turnUuid: string) =>
    api.delete<{ deleted: boolean }>(
      `/sessions/${sessionId}/turns/${turnUuid}`,
    ),
  getChanges: (sessionId: string) =>
    api.get<{ changes: ChangeEntry[] }>(`/sessions/${sessionId}/changes`),
};

export interface ChangeEntry {
  file_path: string;
  /** "edit" (Edit tool) or "create" (Write tool). */
  kind: "edit" | "create";
  /** Unified-diff text for display (empty for creates). */
  diff: string;
  old_text: string;
  new_text: string;
  turn_uuid: string;
  order: number;
}

export interface FileEntry {
  name: string;
  path: string;
  type: "file" | "directory";
}

export const filesystemApi = {
  browse: (projectId: string, path: string = "") =>
    api.get<{ entries: FileEntry[] }>("/fs/browse", {
      params: { project_id: projectId, path },
    }),
  read: (projectId: string, path: string) =>
    api.get<{ content: string }>("/fs/read", {
      params: { project_id: projectId, path },
    }),
  write: (projectId: string, path: string, content: string) =>
    api.put("/fs/write", { project_id: projectId, path, content }),
  home: () => api.get<{ path: string }>("/fs/home"),
  browseAbsolute: (path: string = "") =>
    api.get<{ current_path: string; entries: FileEntry[] }>(
      "/fs/browse-absolute",
      {
        params: { path },
      },
    ),
};

export interface Settings {
  model: string;
  effort: string;
  permission_mode: string;
  tools_enabled: boolean;
  max_turns?: number;
}

export interface Preset {
  id: string;
  name: string;
  settings: Settings;
  created_at: string;
  updated_at: string;
}

export const presetApi = {
  list: () => api.get<{ presets: Preset[] }>("/presets"),
  create: (name: string, settings: Partial<Settings>) =>
    api.post<{ preset: Preset }>("/presets", { name, settings }),
  update: (
    id: string,
    payload: { name?: string; settings?: Partial<Settings> },
  ) => api.put<{ preset: Preset }>(`/presets/${id}`, payload),
  delete: (id: string) => api.delete<{ deleted: boolean }>(`/presets/${id}`),
};

export const settingsApi = {
  getGlobal: () => api.get<{ settings: Settings }>("/settings"),
  updateGlobal: (settings: Partial<Settings>) =>
    api.put<{ settings: Settings }>("/settings", settings),
  getSession: (sessionId: string) =>
    api.get<{ settings: Settings }>(`/settings/session/${sessionId}`),
  updateSession: (sessionId: string, settings: Partial<Settings>) =>
    api.put<{ settings: Settings }>(`/settings/session/${sessionId}`, settings),
};

export const shellApi = {
  start: () => api.post<{ shell_id: string; status: string }>("/shell/start"),
  input: (shellId: string, data: string) =>
    api.post<{ status: string }>(`/shell/${shellId}/input`, { data }),
  resize: (shellId: string, cols: number, rows: number) =>
    api.post<{ status: string }>(`/shell/${shellId}/resize`, { cols, rows }),
  stop: (shellId: string) =>
    api.post<{ status: string }>(`/shell/${shellId}/stop`),
};

export default api;
