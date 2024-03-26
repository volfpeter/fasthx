import warnings
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from typing import Any, Coroutine

from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from typing_extensions import deprecated

from .core_decorators import hx, page
from .typing import JinjaContextFactory, MaybeAsyncFunc, P


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
        - `None` is converted into an empty context.

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

        if route_result is None:
            # Convert no response to empty context.
            return {}

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

    @deprecated("Deprecated and will be removed in the future. Please use `hx()` instead.")
    def __call__(
        self,
        template_name: str,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Deprecated and will be removed in the future. Please use `hx()` instead.

        Alias for `hx()`.
        """
        warnings.warn(
            (
                "Jinja.__call__() is deprecated and will be removed in the future. "
                "Please use hx() instead."
            ),
            DeprecationWarning,
            stacklevel=1,
        )
        return self.hx(template_name, no_data=no_data, make_context=make_context)

    def hx(
        self,
        template_name: str,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name, if the request was an HTMX one.

        Arguments:
            template_name: The name of the Jinja2 template to use.
            no_data: If set, the route will only accept HTMX requests.
            make_context: Route-specific override for the `make_context` property.

        Returns:
            The rendered HTML for HTMX requests, otherwise the route's unchanged return value.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        def render(result: Any, *, context: dict[str, Any], request: Request) -> str | Response:
            return self._make_response(
                template_name,
                jinja_context=make_context(route_result=result, route_context=context),
                request=request,
            )

        return hx(render, no_data=no_data)

    def page(
        self, template_name: str, *, make_context: JinjaContextFactory | None = None
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name. This decorator triggers HTML rendering regardless of whether
        the request was HTMX or not.

        Arguments:
            template_name: The name of the Jinja2 template to use.
            make_context: Route-specific override for the `make_context` property.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        def render(result: Any, *, context: dict[str, Any], request: Request) -> str | Response:
            return self._make_response(
                template_name,
                jinja_context=make_context(route_result=result, route_context=context),
                request=request,
            )

        return page(render)

    @deprecated("Deprecated and will be removed in the future. Please use `hx()` instead.")
    def template(
        self,
        template_name: str,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Deprecated and will be removed in the future. Please use `hx()` instead.

        Alias for `hx()`.
        """
        warnings.warn(
            (
                "Jinja.template() is deprecated and will be removed in the future. "
                "Please use hx() instead."
            ),
            DeprecationWarning,
            stacklevel=1,
        )
        return self.hx(template_name, no_data=no_data, make_context=make_context)

    def _make_response(
        self,
        template_name: str,
        *,
        jinja_context: dict[str, Any],
        request: Request,
    ) -> str | Response:
        """
        Creates the HTML response using the given Jinja template name and context.
        """
        # The reason for returning string from this method is to let `hx()` or `page()` create
        # the HTML response - that way they can copy response headers and do other convenience
        # conversions.
        # The drawback is that users lose some of the baked-in debug utilities of TemplateResponse.
        # This can be worked around by using a rendering context factory that includes the route's
        # dependencies in the Jinja context. Then this method can be overridden to take the Response
        # object from the context and copy the header from it into TemplateResponse.
        result = self.templates.TemplateResponse(
            name=template_name,
            context=jinja_context,
            request=request,
        )
        return result.body.decode(result.charset)
