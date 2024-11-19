import random
from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi import FastAPI
from htmy import Component, ComponentType, Context, html
from pydantic import BaseModel

from fasthx.htmy import HTMY, CurrentRequest, RouteParams

# -- Models


class User(BaseModel):
    """User model."""

    name: str
    birthday: date


# -- HTMY components


@dataclass
class UserListItem:
    """User list item component."""

    user: User

    def htmy(self, context: Context) -> Component:
        return html.li(
            html.span(self.user.name, class_="font-semibold"),
            " ",
            html.em(f"(born {self.user.birthday.isoformat()})"),
            class_="text-lg",
        )


@dataclass
class UserList:
    """User list component that reloads itself every second."""

    users: list[User]

    def htmy(self, context: Context) -> Component:
        # Get the current request and the route parameters from the request.
        request = CurrentRequest.from_context(context)
        route_params = RouteParams.from_context(context)

        # Get the rerenders query parameter if there's one (the index page doesn't have it).
        rerenders: int = route_params.get("rerenders", 0)

        return html.div(
            html.p(html.span("Last request URL: ", class_="font-semibold"), str(request.url)),
            html.p(html.span("Rerenders: ", class_="font-semibold"), str(rerenders)),
            html.hr(),
            html.ul(*(UserListItem(u) for u in self.users), class_="list-disc list-inside"),
            hx_trigger="load delay:1000",
            hx_get=f"/users?rerenders={rerenders+1}",
            hx_swap="outerHTML",
            class_="flex flex-col gap-4",
        )


@dataclass
class Page:
    """Base page layout."""

    content: ComponentType

    def htmy(self, context: Context) -> Component:
        return (
            html.DOCTYPE.html,
            html.html(
                html.head(
                    # Some metadata
                    html.title("FastHX + HTMY example"),
                    html.meta.charset(),
                    html.meta.viewport(),
                    # TailwindCSS
                    html.script(src="https://cdn.tailwindcss.com"),
                    # HTMX
                    html.script(src="https://unpkg.com/htmx.org@2.0.2"),
                ),
                html.body(
                    self.content,
                    class_=(
                        "h-screen w-screen flex flex-col items-center justify-center "
                        " gap-4 bg-slate-800 text-white"
                    ),
                ),
            ),
        )


@dataclass
class IndexPage:
    """Index page."""

    props: Any = None

    def htmy(self, context: Context) -> Component:
        # Lazy load the user list.
        return Page(
            html.div(
                hx_get="/users",
                hx_trigger="load",
                hx_swap="outerHTML",
            ),
        )


# -- Application

# Create the app instance.
app = FastAPI()

# Create the FastHX HTMY instance that renders all route results.
htmy = HTMY()


@app.get("/users")
@htmy.hx(UserList)
def get_users(rerenders: int = 0) -> list[User]:
    """Returns the list of users in random order."""
    result = [
        User(name="John", birthday=date(1940, 10, 9)),
        User(name="Paul", birthday=date(1942, 6, 18)),
        User(name="George", birthday=date(1943, 2, 25)),
        User(name="Ringo", birthday=date(1940, 7, 7)),
    ]
    random.shuffle(result)
    return result


@app.get("/")
@htmy.page(IndexPage)
def index() -> None:
    """The index page of the application."""
    ...
