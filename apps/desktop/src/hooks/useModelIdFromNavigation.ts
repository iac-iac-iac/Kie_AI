import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export function useModelIdFromNavigation(
  models: { id: string }[],
  onSelect: (modelId: string) => void,
) {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const modelId = (location.state as { modelId?: string } | null)?.modelId;
    if (!modelId) return;
    if (!models.some((m) => m.id === modelId)) return;
    onSelect(modelId);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.state, location.pathname, models, navigate, onSelect]);
}
