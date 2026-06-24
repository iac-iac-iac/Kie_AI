import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { applyTheme } from "../../lib/theme";
import { cn } from "../../lib/utils";

function resolvedTheme(theme: "dark" | "light" | "system"): "dark" | "light" {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return theme;
}

export function ThemeToggle({ className }: { className?: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (theme: "dark" | "light") => api.patchSettings({ theme }),
    onSuccess: (data) => {
      applyTheme(data.theme);
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const isDark = resolvedTheme(settingsQuery.data?.theme ?? "dark") === "dark";
  const next = isDark ? "light" : "dark";

  const toggle = () => {
    applyTheme(next);
    mutation.mutate(next);
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={isDark}
      aria-label={t("theme.toggle", { mode: t(`theme.${next}`) })}
      title={t("theme.toggle", { mode: t(`theme.${next}`) })}
      disabled={mutation.isPending}
      onClick={toggle}
      className={cn(
        "group relative h-8 w-[3.25rem] shrink-0 rounded-full p-0.5 shadow-inner transition-all duration-300 ease-out",
        "focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)] focus-visible:outline-none",
        isDark
          ? "bg-gradient-to-r from-slate-700 via-slate-600 to-slate-700"
          : "bg-gradient-to-r from-sky-300 via-amber-200 to-sky-300",
        className,
      )}
    >
      <span className="pointer-events-none absolute inset-0 flex items-center justify-between px-2">
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          className={cn(
            "transition-opacity duration-300",
            isDark ? "opacity-40" : "opacity-90 text-amber-600",
          )}
          aria-hidden
        >
          <circle cx="12" cy="12" r="4" fill="currentColor" />
          <path
            d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          className={cn(
            "transition-opacity duration-300",
            isDark ? "opacity-90 text-slate-200" : "opacity-35",
          )}
          aria-hidden
        >
          <path
            d="M21 14.5A7.5 7.5 0 0 1 9.5 3 6.5 6.5 0 1 0 21 14.5Z"
            fill="currentColor"
          />
        </svg>
      </span>
      <span
        className={cn(
          "relative block h-7 w-7 rounded-full bg-white shadow-[0_2px_8px_rgba(0,0,0,0.18)] transition-transform duration-300 ease-out",
          "group-hover:shadow-[0_3px_10px_rgba(0,0,0,0.22)]",
          isDark ? "translate-x-[1.35rem]" : "translate-x-0",
        )}
      />
    </button>
  );
}
