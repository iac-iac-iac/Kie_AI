import { useQuery } from "@tanstack/react-query";
import { invoke } from "@tauri-apps/api/core";
import { api, ApiError } from "../lib/api";

export type ApiLockReason = "no-key" | "invalid-key" | "network";

async function checkHasApiKey(): Promise<boolean> {
  try {
    return await invoke<boolean>("has_api_key");
  } catch {
    const health = await api.health();
    return health.has_api_key;
  }
}

export function apiLockMessageKey(reason: ApiLockReason | null): string {
  switch (reason) {
    case "invalid-key":
      return "apiKey.invalidKey";
    case "network":
      return "apiKey.networkBlocked";
    default:
      return "apiKey.banner";
  }
}

export function useApiReady() {
  const hasKeyQuery = useQuery({
    queryKey: ["has-api-key"],
    queryFn: checkHasApiKey,
    staleTime: 10_000,
    refetchOnWindowFocus: true,
  });

  const hasKey = hasKeyQuery.data === true;

  const creditsQuery = useQuery({
    queryKey: ["credits"],
    queryFn: () => api.getCredits(),
    enabled: hasKey,
    retry: false,
    staleTime: 30_000,
  });

  const isLoading =
    hasKeyQuery.isLoading ||
    (hasKey && (creditsQuery.isLoading || (creditsQuery.isFetching && !creditsQuery.isFetched)));

  let isReady = false;
  let lockReason: ApiLockReason | null = null;

  if (!hasKeyQuery.isLoading) {
    if (!hasKey) {
      lockReason = "no-key";
    } else if (creditsQuery.isLoading || (creditsQuery.isFetching && !creditsQuery.isFetched)) {
      isReady = false;
    } else if (creditsQuery.isError) {
      const err = creditsQuery.error;
      if (err instanceof ApiError && err.status === 401) {
        lockReason = "invalid-key";
      } else {
        lockReason = "network";
      }
    } else if (creditsQuery.data) {
      isReady = true;
    }
  }

  return { isReady, isLoading, lockReason, hasKey };
}

/** Models/features gate: key saved in app and kie.ai accepts it. */
export function useHasApiKey() {
  const { isReady, isLoading } = useApiReady();
  return { data: isReady, isLoading };
}
