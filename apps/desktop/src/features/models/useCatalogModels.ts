import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ModelCatalogCategory } from "../../components/models/SelectedModelField";

export function useCatalogModels(category: ModelCatalogCategory) {
  const queryKey =
    category === "image"
      ? ["image-models"]
      : category === "video"
        ? ["video-models"]
        : ["audio-models"];

  const queryFn =
    category === "image"
      ? () => api.listImageModels()
      : category === "video"
        ? () => api.listVideoModels()
        : () => api.listAudioModels();

  return useQuery({
    queryKey,
    queryFn,
    retry: 2,
  });
}
