from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

import htmy as h
from fastapi import Request, Response

from .component_selectors import ComponentHeader as _ComponentHeader
from .core_decorators import hx, page
from .typing import ComponentSelector, HTMLRenderer, MaybeAsyncFunc, P, RequestComponentSelector, T

if TYPE_CHECKING:
    from typing_extensions import Self
else:
    Self: TypeAlias = Any  # type: ignore[no-redef]

RequestProcessor: TypeAlias = Callable[[Request], h.Context]
HTMYComponentFactory: TypeAlias = Callable[[T], h.Component]
HTMYComponentSelector: TypeAlias = ComponentSelector[HTMYComponentFactory[T]]


class ComponentHeader(_ComponentHeader[HTMYComponentFactory[T]]):
    """
    `RequestComponentSelector` for HTMY components that takes selects the rendered component
    based on a request header.
    """

    ...


class CurrentRequest:
    """
    HTMY context aware utility for accessing the current request.
    """

    @classmethod
    def to_context(cls, request: Request) -> h.MutableContext:
        """Creates an `htmy` `Context` for the given request."""
        return {Request: request}

    @classmethod
    def from_context(cls, context: h.Context) -> Request:
        """
        Loads the current `Request` instance from the given context.

        Raises:
            KeyError: If the there's no `Request` in the context.
            TypeError: If invalid data is stored for `Request`.
        """
        result = context[Request]
        if isinstance(result, Request):
            return result

        raise TypeError(f"Invalid context data for {cls.__name__}.")


@dataclass(frozen=True, slots=True)
class RouteParams:
    """
    HTMY context aware utility for accessing route parameters (resolved dependencies).

    For convenience, it is a partial, readonly mapping implementation. Supported mapping methods:
    `__contains__`, `__getitem___()`, and `get()`. For more complex use-cases, you can rely on the
    `params` property.
    """

    params: dict[str, Any]
    """Route parameters."""

    def __contains__(self, key: str) -> bool:
        """Membership test operator (`in`)."""
        return key in self.params

    def __getitem__(self, key: str) -> Any:
        """`self[key]` implementation."""
        return self.params[key]

    def get(self, key: str, default: Any = None, /) -> Any:
        """Returns the parameter with the given key."""
        return self.params.get(key, default)

    def to_context(self) -> h.MutableContext:
        """Creates an `htmy` `Context` for this instance."""
        return {RouteParams: self}

    @classmethod
    def from_context(cls, context: h.Context) -> Self:
        """
        Loads the `RouteParams` instance from the given context.

        Raises:
            KeyError: If there's no `RouteParams` in the context.
            TypeError: If invalid data is stored for `RouteParams`.
        """
        result = context[cls]
        if isinstance(result, cls):
            return result

        raise TypeError(f"Invalid context data type for {cls.__name__}.")


@dataclass(frozen=True, slots=True)
class HTMY:
    """
    HTMY renderer utility with FastAPI route decorators.

    The following data is added automatically to every `HTMY` rendering context:

    - The current `Request` that can be retrieved with `CurrentRequest.from_context()` in components.
    - All route parameters (as a `RouteParams` instance) that can be retrieved with
      `RouteParams.from_context()` in components.
    - Everything added through `self.request_processors`.
    - The default context of `self.htmy`.
    """

    htmy: h.Renderer = field(default_factory=h.Renderer)
    """The HTMY renderer to use."""

    no_data: bool = field(default=False, kw_only=True)
    """
    If set, `hx()` routes will only accept HTMX requests.

    Note that if this property is `True`, then the `hx()` decorator's `no_data` argument
    will have no effect.
    """

    request_processors: list[RequestProcessor] = field(default_factory=list, kw_only=True)
    """
    A list of functions that expect the current request and return an `htmy` `Context` that should
    be used during rendering in addition to the default context of `self.htmy`.
    """

    def hx(
        self,
        component_selector: HTMYComponentSelector[T],
        *,
        error_component_selector: HTMYComponentSelector[Exception] | None = None,
        no_data: bool = False,
    ) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, T | Response]]]:
        """
        Decorator for rendering the route's result if the request was an HTMX one.

        Arguments:
            component_selector: The component selector to use.
            error_component_selector: The component selector to use for route error rendering.
            no_data: If set, the route will only accept HTMX requests.
        """
        return hx(
            self._make_render_function(component_selector),
            render_error=None
            if error_component_selector is None
            else self._make_error_render_function(error_component_selector),
            no_data=self.no_data or no_data,
        )

    def page(
        self,
        component_selector: HTMYComponentSelector[T],
        *,
        error_component_selector: HTMYComponentSelector[Exception] | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, T]], Callable[P, Coroutine[None, None, T | Response]]]:
        """
        Decorator for rendering a route's result.

        This decorator triggers HTML rendering regardless of whether the request was HTMX or not.

        Arguments:
            component_selector: The component selector to use.
            error_component_selector: The component selector to use for route error rendering.
        """
        return page(
            self._make_render_function(component_selector),
            render_error=None
            if error_component_selector is None
            else self._make_error_render_function(error_component_selector),
        )

    def _make_render_function(self, component_selector: HTMYComponentSelector[T]) -> HTMLRenderer[T]:
        """Creates a render function that uses the given component selector."""

        async def render(result: T, *, context: dict[str, Any], request: Request) -> str:
            component = (
                component_selector.get_component(request, None)
                if isinstance(component_selector, RequestComponentSelector)
                else component_selector
            )
            return await self.htmy.render(component(result), self._make_render_context(request, context))

        return render

    def _make_error_render_function(
        self, component_selector: HTMYComponentSelector[Exception]
    ) -> HTMLRenderer[Exception]:
        """Creates an error renderer function that uses the given component selector."""

        async def render(result: Exception, *, context: dict[str, Any], request: Request) -> str:
            component = (
                component_selector.get_component(request, result)
                if isinstance(component_selector, RequestComponentSelector)
                else component_selector
            )
            return await self.htmy.render(component(result), self._make_render_context(request, context))

        return render

    def _make_render_context(self, request: Request, route_params: dict[str, Any]) -> h.Context:
        """Creates the HTMY rendering context."""
        # Add the current request to the context.
        result = CurrentRequest.to_context(request)

        # Add all route params to the context.
        result.update(RouteParams(route_params).to_context())

        # Run all request processors and add the result to the context.
        for cp in self.request_processors:
            result.update(cp(request))

        return result
