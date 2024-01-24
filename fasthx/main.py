import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Annotated, Any, ParamSpec, Protocol, TypeVar

from fastapi import Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_P = ParamSpec("_P")
_T = TypeVar("_T")
_Tcontra = TypeVar("_Tcontra", contravariant=True)


def _append_to_signature(
    func: Callable[_P, _T],
    *params: inspect.Parameter,
) -> Callable[_P, _T]:
    """
    Appends the given parameters to the *end* of signature of the given function.

    Notes:
        - This method does not change the function's arguments, it only makes FastAPI's
        dependency resolution system recognize inserted parameters.
        - This is *not* a general purpose method, it is strongly recommended to only
        append keyword-only parameters that have "unique" names that are unlikely to
        be already in the function's signature.

    Arguments:
        func: The function whose signature should be extended.
        params: The parameters to add to the function's signature.

    Returns:
        The received function with an extended `__signature__`.
    """
    signature = inspect.signature(func)
    func.__signature__ = signature.replace(parameters=(*signature.parameters.values(), *params))  # type: ignore[attr-defined]
    return func


class HTMXRenderer(Protocol[_Tcontra]):
    """
    HTMX renderer definition.

    Arguments:
        result: The result of the route the renderer is used on.
        context: Every keyword argument the route received.
        request: The request being served.

    Returns:
        HTML string (it will be automatically converted to `HTMLResponse`) or a `Response` object.
    """

    def __call__(
        self, result: _Tcontra, *, context: dict[str, Any], request: Request
    ) -> str | Response | Awaitable[str | Response]:
        ...


def get_hx_request(request: Request, hx_request: Annotated[str | None, Header()] = None) -> Request | None:
    """
    FastAPI dependency that returns the current request if it is an HTMX one,
    i.e. it contains an `"HX-Request: true"` header.
    """
    return request if hx_request == "true" else None


DependsHXRequest = Annotated[Request | None, Depends(get_hx_request)]
"""Annotated type (dependency) for `get_hx_request()` for FastAPI."""


def hx(
    render: HTMXRenderer[_T], *, no_data: bool = False
) -> Callable[[Callable[_P, _T | Awaitable[_T]]], Callable[_P, Awaitable[_T | Response]]]:
    """
    Decorator that converts a FastAPI route's return value into HTML if the request was
    an HTMX one.

    Arguments:
        render: The render function converting the route's return value to HTML.
        no_data: If set, the route will only accept HTMX requests.
    """

    def decorator(
        func: Callable[_P, _T | Awaitable[_T]],
    ) -> Callable[_P, Awaitable[_T | Response]]:
        @wraps(func)  # type: ignore[arg-type]
        async def wrapper(
            *args: _P.args,
            __hx_request: DependsHXRequest,
            **kwargs: _P.kwargs,
        ) -> _T | Response:
            if no_data and __hx_request is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "This route can only process HTMX requests."
                )

            route_result = func(*args, **kwargs)
            result: _T = await route_result if isinstance(route_result, Awaitable) else route_result
            if __hx_request is None or isinstance(result, Response):
                return result

            rendered = render(result, context=kwargs, request=__hx_request)
            if isinstance(rendered, Awaitable):
                rendered = await rendered

            return HTMLResponse(rendered) if isinstance(rendered, str) else rendered

        return _append_to_signature(
            wrapper,  # type: ignore[arg-type]
            inspect.Parameter(
                "__hx_request",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=DependsHXRequest,
            ),
        )

    return decorator


@dataclass(frozen=True, slots=True)
class Jinja:
    """Jinja2 (renderer) decorator factory."""

    templates: Jinja2Templates
    """The Jinja2 templates of the application."""

    def __call__(
        self, template_name: str, *, no_data: bool = False
    ) -> Callable[[Callable[_P, Any | Awaitable[Any]]], Callable[_P, Awaitable[Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name.

        Arguments:
            template_name: The name of the Jinja2 template to use.
            no_data: If set, the route will only accept HTMX requests.
        """

        def render(result: Any, *, context: dict[str, Any], request: Request) -> HTMLResponse:
            return self.templates.TemplateResponse(name=template_name, request=request, context=result)

        return hx(render, no_data=no_data)

    def template(
        self, template_name: str, *, no_data: bool = False
    ) -> Callable[[Callable[_P, _T | Awaitable[_T]]], Callable[_P, Awaitable[_T | Response]]]:
        """Alias for `__call__()`."""
        return self(template_name, no_data=no_data)
