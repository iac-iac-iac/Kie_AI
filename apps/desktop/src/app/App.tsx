import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { ChatsPage } from "../features/chats/ChatsPage";
import { ImagesPage } from "../features/images/ImagesPage";
import { VideoPage } from "../features/video/VideoPage";
import { AudioPage } from "../features/audio/AudioPage";
import { SettingsLayout } from "../features/settings/SettingsLayout";
import { GeneralTab } from "../features/settings/GeneralTab";
import { InterfaceTab } from "../features/settings/InterfaceTab";
import { ShortcutsTab } from "../features/settings/ShortcutsTab";
import { DiagnosticsTab } from "../features/settings/DiagnosticsTab";
import { BackupTab } from "../features/settings/BackupTab";
import { CreditsTab } from "../features/settings/CreditsTab";
import { ModelCatalogPage } from "../features/models/ModelCatalogPage";
import { api } from "../lib/api";
import { getSidecarUrl } from "../lib/sidecar";
import { applyTheme } from "../lib/theme";
import i18n from "../lib/i18n";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

export function App() {
  useEffect(() => {
    document.documentElement.dataset.theme = "dark";

    void api
      .getSettings()
      .then((settings) => {
        applyTheme(settings.theme);
        void i18n.changeLanguage(settings.locale);
      })
      .catch(() => {
        applyTheme("dark");
      });

    void (async () => {
      try {
        await api.resetSession();
        const has = await invoke<boolean>("has_api_key");
        if (!has) return;
        const sidecarUrl = await getSidecarUrl();
        await invoke("restart_sidecar", { sidecarUrl });
      } catch {
        // Sidecar may not be running yet in dev
      }
    })();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<ChatsPage />} />
            <Route path="images" element={<ImagesPage />} />
            <Route path="video" element={<VideoPage />} />
            <Route path="audio" element={<AudioPage />} />
            <Route path="models/:category" element={<ModelCatalogPage />} />
            <Route path="settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="general" replace />} />
              <Route path="general" element={<GeneralTab />} />
              <Route path="interface" element={<InterfaceTab />} />
              <Route path="shortcuts" element={<ShortcutsTab />} />
              <Route path="diagnostics" element={<DiagnosticsTab />} />
              <Route path="backup" element={<BackupTab />} />
              <Route path="credits" element={<CreditsTab />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
