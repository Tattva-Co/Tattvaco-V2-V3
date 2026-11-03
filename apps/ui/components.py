"""Reusable UI helpers shared by views."""

from typing import Any, Callable, TypeVar

import streamlit as st

from apps.ui.api_client import ApiError

T = TypeVar("T")


def safe_call(fn: Callable[..., T], *args: Any, default: T = None, **kwargs: Any) -> T:
    """Call the API; on failure show the error inline and return ``default``."""
    try:
        return fn(*args, **kwargs)
    except ApiError as exc:
        st.error(f"API error: {exc.message}")
        return default
