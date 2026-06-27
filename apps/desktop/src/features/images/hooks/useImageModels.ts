import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api";

export function useImageModels() {
  const modelsQuery = useQuery({
    queryKey: ["image-models"],
    queryFn: () => api.listImageModels(),
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
    refetchOnWindowFocus: false,
  });
}
