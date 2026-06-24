import { useEffect, useRef } from "react";
import { isEditableTarget, matchHotkey } from "../lib/hotkeys";

export type HotkeyBinding = {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  allowInInput?: boolean;
  preventDefault?: boolean;
  handler: () => void;
};

export function useHotkeys(bindings: HotkeyBinding[], enabled = true) {
  const bindingsRef = useRef(bindings);
  bindingsRef.current = bindings;

  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      for (const binding of bindingsRef.current) {
        if (!matchHotkey(event, binding)) continue;

        const inInput = isEditableTarget(event.target);
        const isCtrlEnter = binding.ctrl && event.key === "Enter";
        if (inInput && !binding.allowInInput && !isCtrlEnter) continue;

        if (binding.preventDefault !== false) {
          event.preventDefault();
        }
        binding.handler();
        return;
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [enabled]);
}
