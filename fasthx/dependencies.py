from collections.abc import Mapping
from typing import TYPE_CHECKING, Annotated, Any, TypeAlias

from fastapi import Depends, Header, Request

RequestAlias: TypeAlias = Mapping[str, Any]
"""
Alias for `Request` arguments.

Workaround for this FastAPI bug: https://github.com/fastapi/fastapi/discussions/12403.
And here's a FastAPI bugfix: https://github.com/fastapi/fastapi/pull/12406.

This workaround should be removed when FastAPI had several new releases with the fix.
"""


def get_hx_request(
    request: Request, hx_request: Annotated[str | None, Header()] = None
) -> RequestAlias | None:
    """
    FastAPI dependency that returns the current request if it is an HTMX one,
    i.e. it contains an `"HX-Request: true"` header.
    """
    return request if hx_request == "true" else None


def get_page_request(request: Request) -> RequestAlias:
    """
    Replacement dependency for `Request` to work around this FastAPI bug:
    https://github.com/fastapi/fastapi/discussions/12403.
    """
    return request


if TYPE_CHECKING:
    DependsHXRequest: TypeAlias = Request | None
    DependsPageRequest: TypeAlias = Request
else:
    DependsHXRequest = Annotated[RequestAlias | Request | None, Depends(get_hx_request)]
    """Annotated type (dependency) for `get_hx_request()` for FastAPI."""

    DependsPageRequest = Annotated[RequestAlias | Request, Depends(get_page_request)]
    """
    Annotated `Request` dependency alias.

    Workaround for this FastAPI bug: https://github.com/fastapi/fastapi/discussions/12403
    """
