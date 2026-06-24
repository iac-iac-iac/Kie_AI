import type { TFunction } from "i18next";
import { ApiError } from "./api";

export function mapApiError(err: unknown, t: TFunction): string {
  if (err instanceof ApiError) {
    const detail = err.message.toLowerCase();
    if (err.status === 401) {
      return t("errors.invalidKey");
    }
    if (err.status === 402) {
      if (detail.includes("session")) {
        return t("errors.sessionLimit");
      }
      return t("errors.insufficientCredits");
    }
    if (err.status === 429) {
      return t("errors.rateLimit");
    }
    if (err.status === 455) {
      return t("errors.maintenance");
    }
    if (err.status === 501) {
      return err.message || t("errors.generationFailed");
    }
    return err.message || t("errors.network");
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return t("errors.network");
}
