from typing import Annotated

from fastapi import Depends, Header, Request


def get_hx_request(request: Request, hx_request: Annotated[str | None, Header()] = None) -> Request | None:
    """
    FastAPI dependency that returns the current request if it is an HTMX one,
    i.e. it contains an `"HX-Request: true"` header.
    """
    return request if hx_request == "true" else None


DependsHXRequest = Annotated[Request | None, Depends(get_hx_request)]
"""Annotated type (dependency) for `get_hx_request()` for FastAPI."""
