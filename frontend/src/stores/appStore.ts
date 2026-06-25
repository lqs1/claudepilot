import { create } from "zustand";

import type { Message, Project, Session } from "@/api";

export type Theme = "light" | "dark" | "system";

interface AppState {
  projects: Project[];
  selectedProjectId: string | null;
  sessions: Session[];
  selectedSessionId: string | null;
  messages: Record<string, Message[]>;
  language: "zh" | "en";
  theme: Theme;
  shellId: string | null;
  setProjects: (projects: Project[]) => void;
  selectProject: (projectId: string | null) => void;
  setSessions: (sessions: Session[]) => void;
  selectSession: (sessionId: string | null) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<Message>,
  ) => void;
  setMessages: (sessionId: string, messages: Message[]) => void;
  setLanguage: (language: "zh" | "en") => void;
  setTheme: (theme: Theme) => void;
  setShellId: (shellId: string | null) => void;
}

function applyTheme(theme: Theme) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const resolved =
    theme === "system" ? (prefersDark ? "dark" : "light") : theme;
  document.documentElement.dataset.theme = resolved;
}

const storedTheme = (localStorage.getItem("theme") as Theme | null) || "system";
applyTheme(storedTheme);

export const useAppStore = create<AppState>((set) => ({
  projects: [],
  selectedProjectId: null,
  sessions: [],
  selectedSessionId: null,
  messages: {},
  language: "zh",
  theme: storedTheme,
  shellId: null,

  setProjects: (projects) => set({ projects }),
  selectProject: (projectId) =>
    set({
      selectedProjectId: projectId,
      sessions: [],
      selectedSessionId: null,
    }),
  setSessions: (sessions) => set({ sessions }),
  selectSession: (sessionId) => set({ selectedSessionId: sessionId }),
  addMessage: (sessionId, message) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] || []), message],
      },
    })),
  updateMessage: (sessionId, messageId, updates) =>
    set((state) => {
      const sessionMessages = state.messages[sessionId] || [];
      const idx = sessionMessages.findIndex((m) => m.id === messageId);
      if (idx === -1) return state;
      const updated = [...sessionMessages];
      updated[idx] = { ...updated[idx], ...updates };
      return {
        messages: { ...state.messages, [sessionId]: updated },
      };
    }),
  setMessages: (sessionId, messages) =>
    set((state) => ({
      messages: { ...state.messages, [sessionId]: messages },
    })),
  setLanguage: (language) => set({ language }),
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    applyTheme(theme);
    set({ theme });
  },
  setShellId: (shellId) => set({ shellId }),
}));
