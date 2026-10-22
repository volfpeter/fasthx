from typing import Annotated

from fastapi import Depends, Header, Request, Response


def get_hx_request(request: Request, hx_request: Annotated[str | None, Header()] = None) -> Request | None:
    """
    FastAPI dependency that returns the current request if it is an HTMX one,
    i.e. it contains an `"HX-Request: true"` header.
    """
    return request if hx_request == "true" else None


def get_page_request(request: Request) -> Request:
    """
    Replacement dependency for `Request` to work around this FastAPI bug:
    https://github.com/fastapi/fastapi/discussions/12403.
    """
    return request


def get_response(response: Response) -> Response:
    """
    Replacement dependency for `Response` to work around this FastAPI bug:
    https://github.com/fastapi/fastapi/discussions/12403.
    """
    return response


DependsHXRequest = Annotated[Request | None, Depends(get_hx_request)]
"""Annotated type (dependency) for `get_hx_request()` for FastAPI."""

DependsPageRequest = Annotated[Request, Depends(get_page_request)]
"""
Annotated `Request` dependency alias.

Workaround for this FastAPI bug: https://github.com/fastapi/fastapi/discussions/12403
"""

DependsResponse = Annotated[Response, Depends(get_response)]
"""
Annotated `Response` dependency alias.

Workaround for this FastAPI bug: https://github.com/fastapi/fastapi/discussions/12403
"""
