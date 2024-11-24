from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, final

from fastapi import Request
from htmy import Component, Context, html

from fasthx.htmy import CurrentRequest, RequestProcessor, RouteParams

from .data import User


class RequestProcessors:
    first_key: ClassVar[str] = "RequestProcessors.first"
    first_value: ClassVar[object] = object()

    second_key: ClassVar[str] = "RequestProcessors.second"
    second_value: ClassVar[object] = object()

    third_key: ClassVar[str] = "RequestProcessors.third"
    third_value: ClassVar[object] = object()

    @classmethod
    def first(cls, request: Request) -> Context:
        return {cls.first_key: cls.first_value}

    @classmethod
    def second(cls, request: Request) -> Context:
        return {cls.second_key: cls.second_value}

    @classmethod
    def third(cls, request: Request) -> Context:
        return {cls.third_key: cls.third_value}

    @classmethod
    def all(cls) -> list[RequestProcessor]:
        return [cls.first, cls.second, cls.third]


class HelloWorld:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Accepts any properties.
        ...

    def htmy(self, context: Context) -> Component:
        return "Hello World!"


@dataclass(frozen=True, slots=True)
class BaseUserComponent:
    user: User

    @final
    def htmy(self, context: Context) -> Component:
        # Test that the current request is always in the context.
        request = CurrentRequest.from_context(context)
        assert isinstance(request, Request)

        # Test that route parameters are always in the context.
        params = RouteParams.from_context(context)
        assert isinstance(params, RouteParams)

        # Test the things that are added by request processors.
        assert context[RequestProcessors.first_key] is RequestProcessors.first_value
        assert context[RequestProcessors.second_key] is RequestProcessors.second_value
        assert context[RequestProcessors.third_key] is RequestProcessors.third_value

        # Render content
        return self._htmy(context)

    def _htmy(self, context: Context) -> Component:
        raise NotImplementedError("Subclasses must implement rendering here.")

    def _render_active(self) -> str:
        return f" (active={self.user.active})"


class UserListItem(BaseUserComponent):
    def _htmy(self, context: Context) -> Component:
        return html.li(self.user.name, self._render_active())


@dataclass(frozen=True, slots=True)
class UserList:
    users: Sequence[User]

    def htmy(self, context: Context) -> Component:
        return html.ul(*(UserListItem(u) for u in self.users))


class Profile:
    class h1(BaseUserComponent):
        def _htmy(self, context: Context) -> Component:
            return html.h1(self.user.name, self._render_active())

    class p(BaseUserComponent):
        def _htmy(self, context: Context) -> Component:
            return html.p(self.user.name, self._render_active())

    class span(BaseUserComponent):
        def _htmy(self, context: Context) -> Component:
            return html.span(self.user.name, self._render_active())
