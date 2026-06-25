import { Moon, Sun, Monitor } from "lucide-react";
import { useEffect, useState } from "react";

import { useAppStore, type Theme } from "@/stores/appStore";

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export function ThemeToggle() {
  const { theme, setTheme } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="flex gap-1 rounded-xl p-1" />;
  }

  return (
    <div
      className="flex gap-1 rounded-xl p-1"
      style={{ boxShadow: "var(--sidebar-pressed)" }}
    >
      {THEMES.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          title={label}
          className={`flex items-center justify-center rounded-lg px-2 py-1.5 text-xs transition-colors ${
            theme === value
              ? "bg-sidebar-active text-sidebar-fg"
              : "text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-fg"
          }`}
        >
          <Icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
