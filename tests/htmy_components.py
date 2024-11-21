from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, final

from fastapi import Request
from htmy import Component, Context, html

from fasthx.htmy import CurrentRequest, RouteParams

from .data import User


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
