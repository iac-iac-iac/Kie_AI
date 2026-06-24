import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api";
import { isSseDegraded } from "../../../lib/events";

export function useGenerations() {
  const queryClient = useQueryClient();

  const generationsQuery = useQuery({
    queryKey: ["generations", "audio"],
    queryFn: () => api.listGenerations("audio"),
    refetchInterval: (query) => {
      if (isSseDegraded()) {
        const items = query.state.data;
        if (items?.some((g) => g.status === "pending" || g.status === "running")) {
          return 2500;
        }
      }
      return false;
    },
  });

  const deleteGeneration = useMutation({
    mutationFn: (id: string) => api.deleteGeneration(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["generations", "audio"] });
    },
  });

  const createGeneration = useMutation({
    mutationFn: ({
      modelId,
      input,
    }: {
      modelId: string;
      input: Record<string, unknown>;
    }) => api.createGeneration(modelId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["generations", "audio"] });
    },
  });

  return {
    generations: generationsQuery.data ?? [],
    isLoading: generationsQuery.isLoading,
    refetch: () => void generationsQuery.refetch(),
    deleteGeneration,
    createGeneration,
  };
}

export function useGeneration(id: string | null) {
  return useQuery({
    queryKey: ["generation", id],
    queryFn: () => api.getGeneration(id!),
    enabled: !!id,
  });
}
