from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Coroutine

from fastapi import Request, Response
from fastapi.templating import Jinja2Templates

from .core_decorators import hx, page
from .typing import (
    ComponentSelector,
    HTMLRenderer,
    JinjaContextFactory,
    MaybeAsyncFunc,
    P,
    RequestComponentSelector,
)


class JinjaPath(str):
    """
    String subclass that can be used to mark a template path as "absolute".

    In this context "absolute" means the template path should be exempt from any prefixing behavior
    during template name resolution.

    Note: calling any of the "mutation" methods (e.g. `.lower()`) of an instance will
    result in a plain `str` object.
    """

    ...


class JinjaContext:
    """
    Core `JinjaContextFactory` implementations.
    """

    @classmethod
    def unpack_object(cls, obj: Any) -> dict[str, Any]:
        """
        Utility function that unpacks an object into a `dict`.

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
            ValueError: If the given object can not be handled by any of the conversion rules.
        """
        if isinstance(obj, dict):
            return obj

        # Covers lists, tuples, sets, etc..
        if isinstance(obj, Collection):
            return {"items": obj}

        object_keys: Iterable[str] | None = None

        # __dict__ should take priority if an object has both this and __slots__.
        if hasattr(obj, "__dict__"):
            # Covers Pydantic models and standard classes.
            object_keys = obj.__dict__.keys()
        elif hasattr(obj, "__slots__"):
            # Covers classes with with __slots__.
            object_keys = obj.__slots__

        if object_keys is not None:
            return {key: getattr(obj, key) for key in object_keys if not key.startswith("_")}

        if obj is None:
            # Convert no response to empty context.
            return {}

        raise ValueError("Result conversion failed, unknown result type.")

    @classmethod
    def unpack_result(cls, *, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
        """
        Jinja context factory that tries to reasonably convert non-`dict` route results
        to valid Jinja contexts (the `route_context` argument is ignored).

        Supports everything that `JinjaContext.unpack_object()` does and follows the same
        conversion rules.

        Raises:
            ValueError: If `route_result` can not be handled by any of the conversion rules.
        """
        return cls.unpack_object(route_result)

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

        Supports everything that `JinjaContext.unpack_object()` does and follows the same
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

    @classmethod
    def use_converters(
        cls,
        convert_route_result: Callable[[Any], dict[str, Any]] | None,
        convert_route_context: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> JinjaContextFactory:
        """
        Creates a `JinjaContextFactory` that uses the provided functions to convert
        `route_result` and `route_context` to a Jinja context.

        The returned `JinjaContextFactory` raises a `ValueError` if the overlapping keys are found.

        Arguments:
            convert_route_result: Function that takes `route_result` and converts it into a `dict`.
                See `JinjaContextFactory` for `route_result` details.
            convert_route_context: Function that takes `route_context` and converts it into a `dict`.
                See `JinjaContextFactory` for `route_context` details.

        Returns:
            The created `JinjaContextFactory`.
        """

        def make_jinja_context(*, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
            rr = {} if convert_route_result is None else convert_route_result(route_result)
            rc = {} if convert_route_context is None else convert_route_context(route_context)
            if len(set(rr.keys()) & set(rc.keys())) > 0:
                raise ValueError("Overlapping keys in route result and route context.")

            rr.update(rc)
            return rr

        return make_jinja_context

    @classmethod
    @lru_cache
    def wrap_as(cls, result_key: str, context_key: str | None = None) -> JinjaContextFactory:
        """
        Creates a `JinjaContextFactory` that wraps the route's result and optionally the route
        context under user-specified keys.

        `result_key` and `context_key` must be different.

        Arguments:
            result_key: The key by which the `route_result` should be accessible in templates.
                See `JinjaContextFactory` for `route_result` details.
            context_key: The key by whih the `route_context` should be accessible in templates.
                If `None` (the default), then the `route_context` will not be accessible.
                See `JinjaContextFactory` for `route_context` details.

        Returns:
            The created `JinjaContextFactory`.

        Raises:
            ValueError: If `result_key` and `context_key` are equal.
        """

        if result_key == context_key:
            raise ValueError("The two keys must be different, merging is not supported.")

        def wrap(*, route_result: Any, route_context: dict[str, Any]) -> dict[str, Any]:
            result = {result_key: route_result}
            if context_key is not None:
                result[context_key] = route_context

            return result

        return wrap


@dataclass(frozen=True, slots=True)
class TemplateHeader:
    """
    Template selector that takes the Jinja template name from a request header.

    This class makes it possible for the client to submit the *key/ID* of the required template
    to the server in a header. The Jinja decorators will then look up and render the requested
    template if it exists. If the client doesn't request a specific template, then `default`
    will be used if it was set, otherwise an exception will be raised.

    By default this class treats template keys as case-insensitive. If you'd like to disable
    this behavior, set `case_sensitive` to `True`.

    This class can also handle route errors if the `error` property is set.

    Implements:
        - `RequestComponentSelector[str]`.
    """

    header: str
    """The header which is used by the client to communicate the *key* of the requested template."""

    templates: dict[str, str]
    """Dictionary that maps template keys to template (file) names."""

    error: type[Exception] | tuple[type[Exception], ...] | None = field(default=None, kw_only=True)
    """The accepted error or errors."""

    default: str | None = field(default=None, kw_only=True)
    """The template to use when the client didn't request a specific one."""

    case_sensitive: bool = field(default=False, kw_only=True)
    """Whether the keys of `templates` are case-sensitive or not (default is `False`)."""

    def __post_init__(self) -> None:
        if not self.case_sensitive:
            object.__setattr__(
                self,
                "templates",
                {k.lower(): v for k, v in self.templates.items()},
            )

    def get_component(self, request: Request, error: Exception | None) -> str:
        """
        Returns the name of the template that was requested by the client.

        If the request doesn't contain a header (with the name `self.header`),
        then `self.default` will be returned if it's not `None`.

        Raises:
            KeyError: If the client requested a specific template but it's unknown, or
                if no template was requested and there's no default either.
        """
        if error is not None and (self.error is None or not isinstance(error, self.error)):
            raise error

        if (key := request.headers.get(self.header, None)) is not None:
            if not self.case_sensitive:
                key = key.lower()

            return self.templates[key]
        elif self.default is None:
            raise KeyError("Default template was not set and header was not found.")
        else:
            return self.default


@dataclass(frozen=True, slots=True)
class Jinja:
    """Jinja2 renderer utility with FastAPI route decorators."""

    templates: Jinja2Templates
    """The Jinja2 templates of the application."""

    make_context: JinjaContextFactory = JinjaContext.unpack_result
    """
    Function that will be used by default to convert a route's return value into
    a Jinja rendering context. The default value is `JinjaContext.unpack_result`.
    """

    no_data: bool = field(default=False, kw_only=True)
    """
    If set, `hx()` routes will only accept HTMX requests.

    Note that if this property is `True`, then the `hx()` decorator's `no_data` argument
    will have no effect.
    """

    def hx(
        self,
        template: ComponentSelector[str],
        *,
        error_template: ComponentSelector[str] | None = None,
        make_context: JinjaContextFactory | None = None,
        no_data: bool = False,
        prefix: str | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's result if the request was an HTMX one.

        Arguments:
            template: The Jinja2 template selector to use.
            error_template: The Jinja2 template selector to use for route error rendering.
            make_context: Route-specific override for the `make_context` property.
            no_data: If set, the route will only accept HTMX requests.
            prefix: Optional template name prefix.

        Returns:
            The rendered HTML for HTMX requests, otherwise the route's unchanged return value.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        return hx(
            self._make_render_function(template, make_context=make_context, prefix=prefix),
            render_error=None
            if error_template is None
            else self._make_render_function(
                error_template, make_context=make_context, prefix=prefix, error_renderer=True
            ),
            no_data=self.no_data or no_data,
        )

    def page(
        self,
        template: ComponentSelector[str],
        *,
        error_template: ComponentSelector[str] | None = None,
        make_context: JinjaContextFactory | None = None,
        prefix: str | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's result.

        This decorator triggers HTML rendering regardless of whether the request was HTMX or not.

        Arguments:
            template: The Jinja2 template selector to use.
            error_template: The Jinja2 template selector to use for route error rendering.
            make_context: Route-specific override for the `make_context` property.
            prefix: Optional template name prefix.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        return page(
            self._make_render_function(template, make_context=make_context, prefix=prefix),
            render_error=None
            if error_template is None
            else self._make_render_function(
                error_template, make_context=make_context, prefix=prefix, error_renderer=True
            ),
        )

    def _make_render_function(
        self,
        template: ComponentSelector[str],
        *,
        make_context: JinjaContextFactory,
        prefix: str | None,
        error_renderer: bool = False,
    ) -> HTMLRenderer[Any]:
        """
        Creates an `HTMLRenderer` with the given configuration.

        Arguments:
            template: The template the renderer function should use.
            make_context: The Jinja rendering context factory to use.
            prefix: Optional template name prefix.
            error_renderer: Whether this is an error renderer creation.
        """

        def render(result: Any, *, context: dict[str, Any], request: Request) -> str | Response:
            template_name = self._resolve_template_name(
                template,
                error=result if error_renderer else None,
                prefix=prefix,
                request=request,
            )
            return self._make_response(
                template_name,
                jinja_context=make_context(route_result=result, route_context=context),
                request=request,
            )

        return render

    def _make_response(
        self,
        template: str,
        *,
        jinja_context: dict[str, Any],
        request: Request,
    ) -> str | Response:
        """
        Creates the HTML response using the given Jinja template name and context.

        Arguments:
            template: The Jinja2 template selector to use.
            jinja_context: The Jinj2 rendering context.
            prefix: Optional template name prefix.
            request: The current request.
        """
        # The reason for returning string from this method is to let `hx()` or `page()` create
        # the HTML response - that way they can copy response headers and do other convenience
        # conversions.
        # The drawback is that users lose some of the baked-in debug utilities of TemplateResponse.
        # This can be worked around by using a rendering context factory that includes the route's
        # dependencies in the Jinja context. Then this method can be overridden to take the Response
        # object from the context and copy the header from it into TemplateResponse.
        result = self.templates.TemplateResponse(
            name=template,
            context=jinja_context,
            request=request,
        )
        return bytes(result.body).decode(result.charset)

    def _resolve_template_name(
        self,
        template: ComponentSelector[str],
        *,
        error: Exception | None = None,
        prefix: str | None,
        request: Request,
    ) -> str:
        """
        Resolves the template selector into a full template name.

        Arguments:
            template: The template selector.
            error: The error raised by the route.
            prefix: Optional template name prefix.
            request: The current request.

        Returns:
            The resolved, full template name.

        Raises:
            ValueError: If template resolution failed.
        """
        if isinstance(template, RequestComponentSelector):
            try:
                result = template.get_component(request, error)
            except KeyError as e:
                raise ValueError("Failed to resolve template name from request.") from e
        elif isinstance(template, str):
            result = template
        else:
            raise ValueError("Unknown template selector.")

        prefix = None if isinstance(result, JinjaPath) else prefix
        result = result.lstrip("/")
        return f"{prefix}/{result}" if prefix else result
