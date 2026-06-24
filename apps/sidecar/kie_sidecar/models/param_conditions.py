from __future__ import annotations

from typing import Any


def matches_condition(values: dict[str, Any], condition: dict[str, Any] | None) -> bool:
    if not condition:
        return True
    for key, expected in condition.items():
        actual = values.get(key)
        if isinstance(expected, bool):
            if bool(actual) != expected:
                return False
        elif actual != expected:
            return False
    return True


def is_param_visible(values: dict[str, Any], visible_when: dict[str, Any] | None) -> bool:
    return matches_condition(values, visible_when)


def is_param_required(
    param_required: bool,
    values: dict[str, Any],
    required_when: dict[str, Any] | None,
) -> bool:
    if required_when is not None:
        return matches_condition(values, required_when)
    return param_required
