# HTMY

The primary focus of this example is how to create [htmy](https://volfpeter.github.io/htmy/) components that work together with `fasthx` and make use of its utilities. The components use TailwindCSS for styling -- if you are not familiar with TailwindCSS, just ignore the `class_="..."` arguments, they are not important from the perspective of `fasthx` and `htmy`. The focus should be on the [htmy](https://volfpeter.github.io/htmy/) components, context usage, and route decorators.

First, let's create an `htmy_app.py` file, import everything that is required for the example, and also define a simple Pydantic `User` model for the application:

```python
import random
from dataclasses import dataclass
from datetime import date

from fastapi import FastAPI
from htmy import Component, Context, html
from pydantic import BaseModel

from fasthx.htmy import HTMY, ComponentHeader, CurrentRequest, RouteParams


class User(BaseModel):
    """User model."""

    name: str
    birthday: date
```

The main content on the user interface will be a user list, so let's start by creating a simple `UserListItem` component:

```python
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
```

As you can see, the component has a single `user` property and it renders an `<li>` HTML element with the user's name and birthday in it.

The next component we need is the user list itself. This is going to be the most complex part of the example:

- To showcase `htmy` context usage, this component will display some information about the application's state in addition to the list of users.
- We will also add a bit of [HTMX](https://htmx.org/attributes/hx-trigger/) to the component to make it re-render every second.

```python
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
```

Most of this code is basic Python and `htmy` usage (including the `hx_*` `HTMX` attributes). The important, `fasthx`-specific things that require special attention are:

- The use of `CurrentRequest.from_context()` to get access to the current `fastapi.Request` instance.
- The use of `RouteParams.from_context()` to get access to every route parameter (resolved FastAPI dependency) as a mapping.
- The `context["user-agent"]` lookup that accesses a value from the context which will be added by a _request processor_ later in the example.

We need one last `htmy` component, the index page. Most of this component is just the basic HTML document structure with some TailwindCSS styling and metadata. There is also a bit of `HTMX` in the `body` for lazy loading the actual page content, the user list we just created.

```python
@dataclass
class IndexPage:
    """Index page with TailwindCSS styling."""

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
                    # Page content: lazy-loaded user list.
                    html.div(hx_get="/users", hx_trigger="load", hx_swap="outerHTML"),
                    class_=(
                        "h-screen w-screen flex flex-col items-center justify-center "
                        " gap-4 bg-slate-800 text-white"
                    ),
                ),
            ),
        )
```

With all the components ready, we can now create the `FastAPI` and `fasthx.htmy.HTMY` instances:

```python
# Create the app instance.
app = FastAPI()

# Create the FastHX HTMY instance that renders all route results.
htmy = HTMY(
    # Register a request processor that adds a user-agent key to the htmy context.
    request_processors=[
        lambda request: {"user-agent": request.headers.get("user-agent")},
    ]
)
```

Note how we added a _request processor_ function to the `HTMY` instance that takes the current FastAPI `Request` and returns a context mapping that is merged into the `htmy` rendering context and made available to every component.

All that remains now is the routing. We need two routes: one that serves the index page, and one that renders the ordered or unordered user list.

The index page route is trivial. The `htmy.page()` decorator expects a component factory (well more precisely a `fasthx.ComponentSelector`) that accepts the route's return value and returns an `htmy` component. Since `IndexPage` has no properties, we use a simple `lambda` to create such a function:

```python
@app.get("/")
@htmy.page(lambda _: IndexPage())
def index() -> None:
    """The index page of the application."""
    ...
```

The `/users` route is a bit more complex: we need to use the `fasthx.htmy.ComponentHeader` utility, because depending on the value of the `X-Component` header (remember the `hx_headers` declaration in `UserOverview.htmy()`) it must render the route's result either with the ordered or unordered version of `UserOverview`.

The route also has a `rerenders` query parameter just to showcase how `fasthx` makes resolved route dependencies accessible to components through the `htmy` rendering context (see `UserOverview.htmy()` for details).

The full route declaration is as follows:

```python
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
```

We finally have everything, all that remains is running our application. Depending on how you [installed FastAPI](https://fastapi.tiangolo.com/#installation), you can do this for example with:

- the `fastapi` CLI like this: `fastapi dev htmy_app.py`,
- or with `uvicorn` like this: `uvicorn htmy_app:app --reload`.

If everything went well, the application will be available at `http://127.0.0.1:8000`.
