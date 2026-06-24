export const SHORTCUT_DEFINITIONS = [
  { id: "navChats", keys: "Ctrl+1" },
  { id: "navImages", keys: "Ctrl+2" },
  { id: "navVideo", keys: "Ctrl+3" },
  { id: "navSettings", keys: "Ctrl+4" },
  { id: "openSettings", keys: "Ctrl+," },
  { id: "sendOrGenerate", keys: "Ctrl+Enter" },
  { id: "newChat", keys: "Ctrl+N" },
  { id: "repeatGeneration", keys: "Ctrl+R" },
  { id: "dismiss", keys: "Escape" },
] as const;

export type ShortcutId = (typeof SHORTCUT_DEFINITIONS)[number]["id"];

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

export function matchHotkey(
  event: KeyboardEvent,
  spec: {
    key: string;
    ctrl?: boolean;
    shift?: boolean;
    alt?: boolean;
  },
): boolean {
  const mod = event.ctrlKey || event.metaKey;
  if (spec.ctrl !== undefined && spec.ctrl !== mod) return false;
  if (spec.shift !== undefined && spec.shift !== event.shiftKey) return false;
  if (spec.alt !== undefined && spec.alt !== event.altKey) return false;
  return event.key.toLowerCase() === spec.key.toLowerCase();
}
