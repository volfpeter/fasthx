import random
from dataclasses import dataclass
from datetime import date

from fastapi import FastAPI
from htmy import Component, ComponentType, Context, html
from pydantic import BaseModel

from fasthx.htmy import HTMY, ComponentHeader, CurrentRequest, RouteParams

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
            html.em(f" (born {self.user.birthday.isoformat()})"),
            class_="text-lg",
        )


@dataclass
class UserOverview:
    """
    Component that shows a user list and some additional info about the application's state.

    The component reloads itself every second.
    """

    users: list[User]
    ordered: bool = False

    def htmy(self, context: Context) -> Component:
        # Load the current request from the context.
        request = CurrentRequest.from_context(context)
        # Load route parameters (resolved dependencies) from the context.
        route_params = RouteParams.from_context(context)
        # Get the user-agent from the context which is added by a request processor.
        user_agent: str = context["user-agent"]
        # Get the rerenders query parameter from the route parameters.
        rerenders: int = route_params["rerenders"]

        # Create the user list item generator.
        user_list_items = (UserListItem(u) for u in self.users)

        # Create the ordered or unordered user list.
        user_list = (
            html.ol(*user_list_items, class_="list-decimal list-inside")
            if self.ordered
            else html.ul(*user_list_items, class_="list-disc list-inside")
        )

        # Randomly decide whether an ordered or unordered list should be rendered next.
        next_variant = random.choice(("ordered", "unordered"))  # noqa: S311

        return html.div(
            # -- Some content about the application state.
            html.p(html.span("Last request: ", class_="font-semibold"), str(request.url)),
            html.p(html.span("User agent: ", class_="font-semibold"), user_agent),
            html.p(html.span("Re-renders: ", class_="font-semibold"), str(rerenders)),
            html.hr(),
            # -- User list.
            user_list,
            # -- HTMX directives.
            hx_trigger="load delay:1000",
            hx_get=f"/users?rerenders={rerenders+1}",
            hx_swap="outerHTML",
            # Send the next component variant in an X-Component header.
            hx_headers=f'{{"X-Component": "{next_variant}"}}',
            # -- Styling
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
                    # Page content
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

    def htmy(self, context: Context) -> Component:
        # Lazy load the user list.
        return Page(html.div(hx_get="/users", hx_trigger="load", hx_swap="outerHTML"))


# -- Application

# Create the app instance.
app = FastAPI()

# Create the FastHX HTMY instance that renders all route results.
htmy = HTMY(
    # Register a request processor that adds a user-agent key to the htmy context.
    request_processors=[
        lambda request: {"user-agent": request.headers.get("user-agent")},
    ]
)


@app.get("/users")
@htmy.hx(
    # Use a header-based component selector that can serve ordered or
    # unordered user lists, depending on what the client requests.
    ComponentHeader(
        "X-Component",
        {
            "ordered": lambda users: UserOverview(users, True),
            "unordered": UserOverview,
        },
        default=UserOverview,
    )
)
def get_users(rerenders: int = 0, ordered_list: bool = False) -> list[User]:
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
@htmy.page(lambda _: IndexPage())
def index() -> None:
    """The index page of the application."""
    ...
