from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from fastapi import Request
from htmy import Component, Context, Renderer
from htmy.renderer import is_streaming_renderer

from .component_selectors import ComponentHeader as _ComponentHeader
from .core_decorators import hx, page
from .typing import ComponentSelector, RequestComponentSelector, T

if TYPE_CHECKING:
    from htmy import MutableContext
    from htmy.renderer.typing import RendererType, StreamingRendererType
    from typing_extensions import Self

    from .core_decorators import HXReturnType, PageReturnType
    from .typing import P, RenderFunction, StreamingRenderFunction

RequestProcessor: TypeAlias = Callable[[Request], Context]
HTMYComponentFactory: TypeAlias = Callable[[T], Component]
HTMYComponentSelector: TypeAlias = ComponentSelector[HTMYComponentFactory[T]]


class ComponentHeader(_ComponentHeader[HTMYComponentFactory[T]]):
    """
    `RequestComponentSelector` for HTMY components that selects the rendered component
    based on a request header.
    """

    ...


class CurrentRequest:
    """
    HTMY context aware utility for accessing the current request.
    """

    @classmethod
    def to_context(cls, request: Request) -> MutableContext:
        """Creates an `htmy` `Context` for the given request."""
        return {Request: request}

    @classmethod
    def from_context(cls, context: Context) -> Request:
        """
        Loads the current `Request` instance from the given context.

        Raises:
            KeyError: If there is no `Request` in the context.
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

    def to_context(self) -> MutableContext:
        """Creates an `htmy` `Context` for this instance."""
        return {RouteParams: self}

    @classmethod
    def from_context(cls, context: Context) -> Self:
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
    - The default context of `self.renderer`.
    """

    renderer: RendererType = field(default_factory=Renderer)
    """The HTMY renderer to use."""

    _: KW_ONLY

    no_data: bool = False
    """
    If set, `hx()` routes will only accept HTMX requests.

    Note that if this property is `True`, then the `hx()` decorator's `no_data` argument
    will have no effect.
    """

    request_processors: list[RequestProcessor] = field(default_factory=list)
    """
    A list of functions that expect the current request and return an `htmy` `Context` that should
    be used during rendering in addition to the default context of `self.renderer`.
    """

    stream: bool = True
    """
    If set, the response will be streamed if the renderer supports it.
    """

    def hx(
        self,
        component_selector: HTMYComponentSelector[T] | None = None,
        *,
        error_component_selector: HTMYComponentSelector[Exception] | None = None,
        no_data: bool = False,
        stream: bool | None = None,
    ) -> HXReturnType[P, T]:
        """
        Decorator for rendering the route's result if the request was an HTMX one.

        Arguments:
            component_selector: An optional component selector to use. If not provided, it is
                assumed the route returns a component that should be rendered as is.
            error_component_selector: The component selector to use for route error rendering.
            no_data: If set, the route will only accept HTMX requests.
            stream: If set, overrides the class-level `stream` setting for this decorator.
        """
        selector = _default_component_selector if component_selector is None else component_selector
        should_stream = self.stream if stream is None else stream

        if should_stream and is_streaming_renderer(self.renderer):
            return hx(
                self._make_render_function(
                    selector,
                    streaming_renderer=self.renderer,
                ),
                render_error=None
                if error_component_selector is None
                else self._make_error_render_function(
                    error_component_selector,
                    streaming_renderer=self.renderer,
                ),
                no_data=self.no_data or no_data,
                stream=True,
            )
        else:
            return hx(
                self._make_render_function(
                    selector,
                    renderer=self.renderer,
                ),
                render_error=None
                if error_component_selector is None
                else self._make_error_render_function(
                    error_component_selector,
                    renderer=self.renderer,
                ),
                no_data=self.no_data or no_data,
            )

    def page(
        self,
        component_selector: HTMYComponentSelector[T] | None = None,
        *,
        error_component_selector: HTMYComponentSelector[Exception] | None = None,
        stream: bool | None = None,
    ) -> PageReturnType[P, T]:
        """
        Decorator for rendering a route's result.

        This decorator triggers HTML rendering regardless of whether the request was HTMX or not.

        Arguments:
            component_selector: An optional component selector to use. If not provided, it is
                assumed the route returns a component that should be rendered as is.
            error_component_selector: The component selector to use for route error rendering.
            stream: If set, overrides the class-level `stream` setting for this decorator.
        """
        selector = _default_component_selector if component_selector is None else component_selector
        should_stream = self.stream if stream is None else stream

        if should_stream and is_streaming_renderer(self.renderer):
            return page(
                self._make_render_function(
                    selector,
                    streaming_renderer=self.renderer,
                ),
                render_error=None
                if error_component_selector is None
                else self._make_error_render_function(
                    error_component_selector,
                    streaming_renderer=self.renderer,
                ),
                stream=True,
            )
        else:
            return page(
                self._make_render_function(
                    selector,
                    renderer=self.renderer,
                ),
                render_error=None
                if error_component_selector is None
                else self._make_error_render_function(
                    error_component_selector,
                    renderer=self.renderer,
                ),
            )

    async def render_component(self, component: Component, request: Request) -> str:
        """
        Renders the given component.

        This method is useful for rendering components directly, outside of the context of a route
        (meaning no access to route parameters), for example in exception handlers.

        The method adds all the usual data to the `htmy` rendering context, including the result of
        all request processors. There is no access to route parameters though, so while `RouteParams`
        will be in the context, it will be empty.

        Arguments:
            component: The component to render.
            request: The current request.

        Returns:
            The rendered component.
        """
        return await self.renderer.render(component, self._make_render_context(request, {}))

    @overload
    def _make_render_function(
        self,
        component_selector: HTMYComponentSelector[T],
        *,
        renderer: None = None,
        streaming_renderer: StreamingRendererType,
    ) -> StreamingRenderFunction[T]: ...

    @overload
    def _make_render_function(
        self,
        component_selector: HTMYComponentSelector[T],
        *,
        renderer: RendererType,
        streaming_renderer: None = None,
    ) -> RenderFunction[T]: ...

    def _make_render_function(
        self,
        component_selector: HTMYComponentSelector[T],
        *,
        renderer: RendererType | None = None,
        streaming_renderer: StreamingRendererType | None = None,
    ) -> RenderFunction[T] | StreamingRenderFunction[T]:
        """
        Creates a render function that uses the given component selector.

        Arguments:
            component_selector: The component selector to use.
            renderer: The renderer to use for non-streaming rendering. Must be `None` if
                `streaming_renderer` is provided.
            streaming_renderer: The streaming renderer to use for streaming rendering. Must be
                `None` if `renderer` is provided.

        Returns:
            A render function (streaming or non-streaming based on which renderer is provided).
        """
        if streaming_renderer is not None:
            # This function must be sync and execute the component selector before returning
            # the async iterator, otherwise the component selector would only be executed as
            # part of the async iterator, so during response streaming.
            def streaming_render(
                result: T, *, context: dict[str, Any], request: Request
            ) -> AsyncIterator[str]:
                component = (
                    component_selector.get_component(request, None)
                    if isinstance(component_selector, RequestComponentSelector)
                    else component_selector
                )
                return streaming_renderer.stream(
                    component(result), self._make_render_context(request, context)
                )

            return streaming_render
        elif renderer is not None:

            async def render(result: T, *, context: dict[str, Any], request: Request) -> str:
                component = (
                    component_selector.get_component(request, None)
                    if isinstance(component_selector, RequestComponentSelector)
                    else component_selector
                )
                return await renderer.render(component(result), self._make_render_context(request, context))

            return render
        else:
            raise ValueError("No renderer provided.")

    @overload
    def _make_error_render_function(
        self,
        component_selector: HTMYComponentSelector[Exception],
        *,
        renderer: None = None,
        streaming_renderer: StreamingRendererType,
    ) -> StreamingRenderFunction[Exception]: ...

    @overload
    def _make_error_render_function(
        self,
        component_selector: HTMYComponentSelector[Exception],
        *,
        renderer: RendererType,
        streaming_renderer: None = None,
    ) -> RenderFunction[Exception]: ...

    def _make_error_render_function(
        self,
        component_selector: HTMYComponentSelector[Exception],
        *,
        renderer: RendererType | None = None,
        streaming_renderer: StreamingRendererType | None = None,
    ) -> RenderFunction[Exception] | StreamingRenderFunction[Exception]:
        """
        Creates an error renderer function that uses the given component selector.

        Arguments:
            component_selector: The component selector to use for error rendering.
            renderer: The renderer to use for non-streaming rendering. Must be `None` if
                `streaming_renderer` is provided.
            streaming_renderer: The streaming renderer to use for streaming rendering. Must be
                `None` if `renderer` is provided.

        Returns:
            An error render function (streaming or non-streaming based on which renderer is provided).
        """
        if streaming_renderer is not None:
            # This function must be sync and execute the component selector before returning
            # the async iterator, otherwise the component selector would only be executed as
            # part of the async iterator, so during response streaming.
            def streaming_render(
                result: Exception, *, context: dict[str, Any], request: Request
            ) -> AsyncIterator[str]:
                component = (
                    component_selector.get_component(request, result)
                    if isinstance(component_selector, RequestComponentSelector)
                    else component_selector
                )
                return streaming_renderer.stream(
                    component(result), self._make_render_context(request, context)
                )

            return streaming_render
        elif renderer is not None:

            async def render(result: Exception, *, context: dict[str, Any], request: Request) -> str:
                component = (
                    component_selector.get_component(request, result)
                    if isinstance(component_selector, RequestComponentSelector)
                    else component_selector
                )
                return await renderer.render(component(result), self._make_render_context(request, context))

            return render
        else:
            raise ValueError("No renderer provided.")

    def _make_render_context(self, request: Request, route_params: dict[str, Any]) -> Context:
        """
        Creates the `htmy` rendering context for the given request and route parameters.

        Arguments:
            request: The current request.
            route_params: The route parameters.

        Returns:
            The `htmy` rendering context.
        """
        # Add the current request to the context.
        result = CurrentRequest.to_context(request)

        # Add all route params to the context.
        result.update(RouteParams(route_params).to_context())

        # Run all request processors and add the result to the context.
        for cp in self.request_processors:
            result.update(cp(request))

        return result


def _default_component_selector(route_result: Any) -> Component:
    """
    Default component selector that returns the route result as is.

    It is assumed (and not validated) that the route result is a `htmy.Component` when
    this component selector is used. Otherwise rendering will fail.
    """
    return route_result  # type: ignore[no-any-return]
