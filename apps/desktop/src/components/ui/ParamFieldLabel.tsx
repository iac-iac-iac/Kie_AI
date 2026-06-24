import { useCallback, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

export function paramLabel(t: TFunction, name: string): string {
  const key = `params.${name}.label`;
  const translated = t(key);
  return translated === key ? name : translated;
}

export function paramHint(t: TFunction, name: string): string | null {
  const key = `params.${name}.hint`;
  const translated = t(key);
  return translated === key ? null : translated;
}

export function paramOptionLabel(
  t: TFunction,
  paramName: string,
  value: string,
): string {
  const safeValue = value.replace(/:/g, "__");
  const key = `params.${paramName}.options.${safeValue}`;
  const translated = t(key);
  return translated === key ? value : translated;
}

const TOOLTIP_WIDTH = 224;
const TOOLTIP_MARGIN = 8;

export function ParamFieldLabel({
  name,
  required,
}: {
  name: string;
  required?: boolean;
}) {
  const { t } = useTranslation();
  const label = paramLabel(t, name);
  const hint = paramHint(t, name);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [tooltip, setTooltip] = useState<{ top: number; left: number } | null>(null);

  const showTooltip = useCallback(() => {
    const el = btnRef.current;
    if (!el || !hint) return;
    const rect = el.getBoundingClientRect();
    let left = rect.left;
    if (left + TOOLTIP_WIDTH > window.innerWidth - TOOLTIP_MARGIN) {
      left = window.innerWidth - TOOLTIP_WIDTH - TOOLTIP_MARGIN;
    }
    if (left < TOOLTIP_MARGIN) left = TOOLTIP_MARGIN;
    setTooltip({ top: rect.bottom + 6, left });
  }, [hint]);

  const hideTooltip = useCallback(() => setTooltip(null), []);

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-sm font-medium text-primary">
        {label}
        {required && <span className="text-status-error"> *</span>}
      </span>
      {hint && (
        <>
          <button
            ref={btnRef}
            type="button"
            tabIndex={0}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-[var(--glass-border)] text-[10px] leading-none text-subtle hover:border-[var(--accent-ring)] hover:text-accent"
            aria-label={hint}
            onMouseEnter={showTooltip}
            onMouseLeave={hideTooltip}
            onFocus={showTooltip}
            onBlur={hideTooltip}
          >
            ?
          </button>
          {tooltip &&
            createPortal(
              <span
                role="tooltip"
                className="glass-tooltip pointer-events-none fixed z-[9999] w-56 rounded-lg px-2.5 py-2 text-xs font-normal leading-snug text-primary shadow-xl"
                style={{ top: tooltip.top, left: tooltip.left }}
              >
                {hint}
              </span>,
              document.body,
            )}
        </>
      )}
    </div>
  );
}
