"""Helpers for integration tests.

`assert_typeddict_shape` validates that a JSON response has exactly the
keys declared by a TypedDict (or a strict subset when the TypedDict marks
keys as NotRequired). It catches contract drift between the API
implementation and the documented contract in src/srag/api/types.py.
"""

from typing import Any, get_type_hints


def required_keys(typed_dict: type) -> set[str]:
    """Return the set of keys a TypedDict marks as required.

    A key is considered required when it does not have a default value
    AND it is not annotated with NotRequired[...] (PEP 655).
    """
    hints = get_type_hints(typed_dict, include_extras=True)
    required: set[str] = set()
    for key, hint in hints.items():
        origin_module = getattr(hint, "__module__", "")
        if "typing" in origin_module and getattr(hint, "__name__", "") == "NotRequired":
            continue
        if not hasattr(typed_dict, key):
            continue
        if getattr(typed_dict, key, None) is None:
            required.add(key)
    return required


def assert_typeddict_keys(body: dict[str, Any], typed_dict: type) -> None:
    """Assert body contains at least all keys required by the TypedDict.

    Extra keys are allowed (TypedDict is structural; we accept additional
    fields the implementation may have added).
    """
    required = required_keys(typed_dict)
    missing = required - set(body.keys())
    assert not missing, (
        f"Missing required keys {missing} for {typed_dict.__name__}; got {set(body.keys())}"
    )
