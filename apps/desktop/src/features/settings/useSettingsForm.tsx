import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import i18n from "../../lib/i18n";
import { api, type AppSettings } from "../../lib/api";
import { applyTheme } from "../../lib/theme";

interface SettingsFormContextValue {
  form: AppSettings;
  update: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => void;
  saveSettings: ReturnType<typeof useMutation<AppSettings, Error, Partial<AppSettings>>>;
  isLoading: boolean;
}

const SettingsFormContext = createContext<SettingsFormContextValue | null>(null);

export function SettingsFormProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  const [form, setForm] = useState<AppSettings | null>(null);

  useEffect(() => {
    if (settingsQuery.data) {
      setForm(settingsQuery.data);
      applyTheme(settingsQuery.data.theme);
      void i18n.changeLanguage(settingsQuery.data.locale);
    }
  }, [settingsQuery.data]);

  const saveSettings = useMutation<AppSettings, Error, Partial<AppSettings>>({
    mutationFn: (patch) => api.patchSettings(patch),
    onSuccess: (data: AppSettings) => {
      setForm(data);
      applyTheme(data.theme);
      void i18n.changeLanguage(data.locale);
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  if (!form) {
    return null;
  }

  return (
    <SettingsFormContext.Provider
      value={{
        form,
        update,
        saveSettings,
        isLoading: settingsQuery.isLoading,
      }}
    >
      {children}
    </SettingsFormContext.Provider>
  );
}

export function useSettingsForm() {
  const ctx = useContext(SettingsFormContext);
  if (!ctx) {
    throw new Error("useSettingsForm must be used within SettingsFormProvider");
  }
  return ctx;
}
