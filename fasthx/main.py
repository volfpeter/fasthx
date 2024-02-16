import inspect
from collections.abc import Awaitable, Callable, Collection, Iterable
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


class JinjaContextFactory(Protocol):
    """
    Protocol definition for methods that convert a FastAPI route's result and route context
    (i.e. the route's arguments) into a Jinja context (`dict`).

    Arguments:
        route_result: The result of the route.
        route_context: Every keyword argument the route received.

    Returns:
        The Jinja context dictionary.

    Raises:
        ValueError: If converting the arguments to a Jinja context fails.
    """

    def __call__(self, *, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
        ...


class JinjaContext:
    """
    Core `JinjaContextFactory` implementations.
    """

    @classmethod
    def unpack_result(cls, *, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
        """
        Jinja context factory that tries to reasonably convert non-`dict` route results
        to valid Jinja contexts (the `route_context` argument is ignored).

        Supports `dict` and `Collection` instances, plus anything with `__dict__` or `__slots__`
        attributes, for example Pydantic models, dataclasses, or "standard" class instances.

        Conversion rules:

        - `dict`: returned as is.
        - `Collection`: returned as `{"items": route_context}`, available in templates as `items`.
        - Objects with `__dict__` or `__slots__`: known keys are taken from `__dict__` or `__slots__`
          and the context will be created as `{key: getattr(route_result, key) for key in keys}`,
          omitting property names starting with an underscore.

        Raises:
            ValueError: If `route_result` can not be handled by any of the conversion rules.
        """
        if isinstance(route_result, dict):
            return route_result

        # Covers lists, tuples, sets, etc..
        if isinstance(route_result, Collection):
            return {"items": route_result}

        object_keys: Iterable[str] | None = None

        # __dict__ should take priority if an object has both this and __slots__.
        if hasattr(route_result, "__dict__"):
            # Covers Pydantic models and standard classes.
            object_keys = route_result.__dict__.keys()
        elif hasattr(route_result, "__slots__"):
            # Covers classes with with __slots__.
            object_keys = route_result.__slots__

        if object_keys is not None:
            return {key: getattr(route_result, key) for key in object_keys if not key.startswith("_")}

        raise ValueError("Result conversion failed, unknown result type.")

    @classmethod
    def unpack_result_with_route_context(
        cls,
        *,
        route_result: Any,
        route_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Jinja context factory that tries to reasonably convert non-`dict` route results
        to valid Jinja contexts, also including every key-value pair from `route_context`.

        Supports everything that `JinjaContext.unpack_result()` does and follows the same
        conversion rules.

        Raises:
            ValueError: If `JinjaContext.unpack_result()` raises an error or if there's
                a key conflict between `route_result` and `route_context`.
        """
        result = cls.unpack_result(route_result=route_result, route_context=route_context)
        if len(set(result.keys()) & set(route_context.keys())) > 0:
            raise ValueError("Overlapping keys in route result and route context.")

        # route_context is the keyword args of the route collected into a dict. Update and
        # return this dict rather than result, as the result might be the same object that
        # was returned by the route and someone may have a reference to it.
        route_context.update(result)
        return route_context


@dataclass(frozen=True, slots=True)
class Jinja:
    """Jinja2 (renderer) decorator factory."""

    templates: Jinja2Templates
    """The Jinja2 templates of the application."""

    make_context: JinjaContextFactory = JinjaContext.unpack_result
    """
    Function that will be used by default to convert a route's return value into
    a Jinja rendering context. The default value is `JinjaContext.unpack_result`.
    """

    def __call__(
        self,
        template_name: str,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
    ) -> Callable[[Callable[_P, Any | Awaitable[Any]]], Callable[_P, Awaitable[Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name.

        Arguments:
            template_name: The name of the Jinja2 template to use.
            no_data: If set, the route will only accept HTMX requests.
            make_context: Route-specific override for the `make_context` property.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        def render(result: Any, *, context: dict[str, Any], request: Request) -> HTMLResponse:
            return self._make_response(
                template_name,
                jinja_context=make_context(route_result=result, route_context=context),
                request=request,
            )

        return hx(render, no_data=no_data)

    def template(
        self,
        template_name: str,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
    ) -> Callable[[Callable[_P, Any | Awaitable[Any]]], Callable[_P, Awaitable[Any | Response]]]:
        """Alias for `__call__()`."""
        return self(template_name, no_data=no_data, make_context=make_context)

    def _make_response(
        self,
        template_name: str,
        *,
        jinja_context: dict[str, Any],
        request: Request,
    ) -> HTMLResponse:
        """
        Creates the HTML response using the given Jinja template name and context.
        """
        return self.templates.TemplateResponse(name=template_name, context=jinja_context, request=request)
