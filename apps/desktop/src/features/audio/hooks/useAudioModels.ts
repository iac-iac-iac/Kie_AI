import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api";

export function useAudioModels() {
  const modelsQuery = useQuery({
    queryKey: ["audio-models"],
    queryFn: () => api.listAudioModels(),
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
