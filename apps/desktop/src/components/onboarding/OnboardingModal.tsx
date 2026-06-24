import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";

const STORAGE_KEY = "kie_onboarding_v1_done";

export function isOnboardingDone(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function markOnboardingDone() {
  try {
    localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    // ignore
  }
}

export function OnboardingModal() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(() => !isOnboardingDone());
  const [step, setStep] = useState(0);

  if (!open) return null;

  const finish = () => {
    markOnboardingDone();
    setOpen(false);
  };

  const steps = [
    {
      title: t("onboarding.welcomeTitle"),
      body: t("onboarding.welcomeBody"),
    },
    {
      title: t("onboarding.apiKeyTitle"),
      body: t("onboarding.apiKeyBody"),
    },
    {
      title: t("onboarding.readyTitle"),
      body: t("onboarding.readyBody"),
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div
        className="glass-panel w-full max-w-md rounded-2xl border border-[var(--glass-border)] p-6 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
      >
        <p className="text-xs font-medium tracking-wide text-subtle uppercase">
          {t("onboarding.step", { current: step + 1, total: steps.length })}
        </p>
        <h2 id="onboarding-title" className="mt-2 text-xl font-semibold text-primary">
          {current.title}
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-muted">{current.body}</p>

        {step === 1 && (
          <Link
            to="/settings"
            className="mt-4 inline-block text-sm font-medium text-accent underline-offset-2 hover:underline"
            onClick={finish}
          >
            {t("onboarding.openSettings")}
          </Link>
        )}

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            type="button"
            className="text-sm text-subtle hover:text-primary"
            onClick={finish}
          >
            {t("onboarding.skip")}
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button type="button" variant="outline" onClick={() => setStep((s) => s - 1)}>
                {t("onboarding.back")}
              </Button>
            )}
            <Button
              type="button"
              onClick={() => {
                if (isLast) finish();
                else setStep((s) => s + 1);
              }}
            >
              {isLast ? t("onboarding.start") : t("onboarding.next")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
