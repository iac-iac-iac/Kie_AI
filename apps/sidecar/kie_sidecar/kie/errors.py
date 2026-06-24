from __future__ import annotations


class KieApiError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class KieAuthError(KieApiError):
    pass


class KieInsufficientCreditsError(KieApiError):
    pass


class KieRateLimitError(KieApiError):
    pass


def map_kie_error(code: int, message: str) -> KieApiError:
    if code == 401:
        return KieAuthError(code, message or "Authentication required or failed")
    if code == 402:
        return KieInsufficientCreditsError(code, message or "Insufficient credits")
    if code == 429:
        return KieRateLimitError(code, message or "Rate limit exceeded")
    return KieApiError(code, message or "Kie API error")
