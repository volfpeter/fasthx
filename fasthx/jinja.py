from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from typing import Any, Coroutine, TypeAlias

from fastapi import Request, Response
from fastapi.templating import Jinja2Templates

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
class TemplateHeader:
    """
    Template selector that takes the Jinja template name from a request header.

    This class makes it possible for the client to submit the *key* of the required template
    to the server in a header. The Jinja decorators will then look up and render the requested
    template if it exists. If the client doesn't request a specific template, then `default`
    will be used if it was set, otherwise an exception will be raised.

    By default this class treats template keys as key-insensitive. If you'd like to disable
    this behavior, set `case_sensitive` to `True`.
    """

    header: str
    """The header which is used by the client to communicate the *key* of the requested template."""

    templates: dict[str, str]
    """Dictionary that maps template keys to template (file) names."""

    default: str | None = field(default=None, kw_only=True)
    """The template to use when the client didn't request a specific one."""

    case_sensitive: bool = field(default=False, kw_only=True)
    """Whether the keys of `templates` are case sensitive or not (default is case insensitive)."""

    def __post_init__(self) -> None:
        if not self.case_sensitive:
            object.__setattr__(
                self,
                "templates",
                {k.lower(): v for k, v in self.templates.items()},
            )

    def get_template_name(self, request: Request) -> str:
        """
        Returns the name of the template that was requested by the client.

        If the request doesn't contain a header (with the name `self.header`),
        then `self.default` will be returned if it's not `None`.

        Raises:
            KeyError: If the client requested a specific template but it's unknown, or
                if no template was requested and there's no default either.
        """
        if (key := request.headers.get(self.header, None)) is not None:
            if not self.case_sensitive:
                key = key.lower()

            return self.templates[key]
        elif self.default is None:
            raise KeyError("Default template was not set and header was not found.")
        else:
            return self.default


TemplateSelector: TypeAlias = TemplateHeader | str
"""Type alias for known template selectors."""


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

    def hx(
        self,
        template: TemplateSelector,
        *,
        no_data: bool = False,
        make_context: JinjaContextFactory | None = None,
        prefix: str | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name, if the request was an HTMX one.

        Arguments:
            template: The Jinja2 template selector to use.
            no_data: If set, the route will only accept HTMX requests.
            make_context: Route-specific override for the `make_context` property.
            prefix: Optional template name prefix.

        Returns:
            The rendered HTML for HTMX requests, otherwise the route's unchanged return value.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        def render(result: Any, *, context: dict[str, Any], request: Request) -> str | Response:
            return self._make_response(
                template,
                jinja_context=make_context(route_result=result, route_context=context),
                prefix=prefix,
                request=request,
            )

        return hx(render, no_data=no_data)

    def page(
        self,
        template: TemplateSelector,
        *,
        make_context: JinjaContextFactory | None = None,
        prefix: str | None = None,
    ) -> Callable[[MaybeAsyncFunc[P, Any]], Callable[P, Coroutine[None, None, Any | Response]]]:
        """
        Decorator for rendering a route's return value to HTML using the Jinja2 template
        with the given name. This decorator triggers HTML rendering regardless of whether
        the request was HTMX or not.

        Arguments:
            template: The Jinja2 template selector to use.
            make_context: Route-specific override for the `make_context` property.
            prefix: Optional template name prefix.
        """
        if make_context is None:
            # No route-specific override.
            make_context = self.make_context

        def render(result: Any, *, context: dict[str, Any], request: Request) -> str | Response:
            return self._make_response(
                template,
                jinja_context=make_context(route_result=result, route_context=context),
                prefix=prefix,
                request=request,
            )

        return page(render)

    def _make_response(
        self,
        template: TemplateSelector,
        *,
        jinja_context: dict[str, Any],
        prefix: str | None = None,
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
        template_name = self._resolve_template_name(template, prefix=prefix, request=request)
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

    def _resolve_template_name(
        self,
        template: TemplateSelector,
        *,
        prefix: str | None,
        request: Request,
    ) -> str:
        """
        Resolves the template selector into a full template name.

        Arguments:
            template: The template selector.
            prefix: Optional template name prefix.
            request: The current request.

        Returns:
            The resolved, full template name.

        Raises:
            ValueError: If template resolution failed.
        """
        if isinstance(template, TemplateHeader):
            try:
                result = template.get_template_name(request)
            except KeyError as e:
                raise ValueError("Failed to resolve template name from request.") from e
        elif isinstance(template, str):
            result = template
        else:
            raise ValueError("Unknown template selector.")

        result = result.lstrip("/")
        return f"{prefix}/{result}" if prefix else result
