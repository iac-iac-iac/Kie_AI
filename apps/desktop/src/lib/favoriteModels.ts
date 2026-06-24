const STORAGE_KEY = "kie_favorite_models";

function readRaw(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((id): id is string => typeof id === "string");
  } catch {
    return [];
  }
}

function write(ids: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // ignore quota / private mode
  }
}

export function getFavorites(): string[] {
  return readRaw();
}

export function isFavorite(modelId: string): boolean {
  return readRaw().includes(modelId);
}

export function toggleFavorite(modelId: string): boolean {
  const current = readRaw();
  const exists = current.includes(modelId);
  const next = exists ? current.filter((id) => id !== modelId) : [...current, modelId];
  write(next);
  return !exists;
}

export function sortFavoritesFirst<T extends { id: string }>(models: T[]): T[] {
  const favSet = new Set(readRaw());
  const favorites: T[] = [];
  const rest: T[] = [];
  for (const model of models) {
    if (favSet.has(model.id)) favorites.push(model);
    else rest.push(model);
  }
  return [...favorites, ...rest];
}

export function groupWithFavorites<T extends { id: string }>(
  models: T[],
): { favorites: T[]; rest: T[] } {
  const favSet = new Set(readRaw());
  const favorites: T[] = [];
  const rest: T[] = [];
  for (const model of models) {
    if (favSet.has(model.id)) favorites.push(model);
    else rest.push(model);
  }
  return { favorites, rest };
}
