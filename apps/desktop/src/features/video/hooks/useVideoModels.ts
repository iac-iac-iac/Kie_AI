import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api";

export function useVideoModels() {
  const modelsQuery = useQuery({
    queryKey: ["video-models"],
    queryFn: () => api.listVideoModels(),
    retry: 2,
  });

  return {
    models: modelsQuery.data ?? [],
    isLoading: modelsQuery.isLoading,
    isError: modelsQuery.isError,
    refetch: () => void modelsQuery.refetch(),
  };
}

export function useModelSchema(modelId: string | null) {
  return useQuery({
    queryKey: ["model-schema", modelId],
    queryFn: () => api.getModelSchema(modelId!),
    enabled: !!modelId,
  });
}
