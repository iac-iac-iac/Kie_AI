type ToastListener = (message: string) => void;

let listener: ToastListener | null = null;

export function showToast(message: string): void {
  listener?.(message);
}

export function subscribeToast(fn: ToastListener): () => void {
  listener = fn;
  return () => {
    if (listener === fn) listener = null;
  };
}
