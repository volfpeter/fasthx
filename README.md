![Tests](https://github.com/volfpeter/fasthx/actions/workflows/tests.yml/badge.svg)
![Linters](https://github.com/volfpeter/fasthx/actions/workflows/linters.yml/badge.svg)
![Documentation](https://github.com/volfpeter/fasthx/actions/workflows/build-docs.yml/badge.svg)
![PyPI package](https://img.shields.io/pypi/v/fasthx?color=%2334D058&label=PyPI%20Package)

**Source code**: [https://github.com/volfpeter/fasthx](https://github.com/volfpeter/fasthx)

**Documentation and examples**: [https://volfpeter.github.io/fasthx](https://volfpeter.github.io/fasthx/)

# FastHX

FastAPI server-side rendering with built-in HTMX support.

Key features:

- **Decorator syntax** that works with FastAPI as one would expect, no need for unused or magic dependencies in routes.
- Built for **HTMX**, but can be used without it.
- Works with **any templating engine** or server-side rendering library, e.g. `htmy`, `jinja2`, or `dominate`.
- Gives the rendering engine **access to all dependencies** of the decorated route.
- HTMX **routes work as expected** if they receive non-HTMX requests, so the same route can serve data and render HTML at the same time.
- **Response headers** you set in your routes are kept after rendering, as you would expect in FastAPI.
- **Correct typing** makes it possible to apply other (typed) decorators to your routes.
- Works with both **sync** and **async routes**.

## Installation

The package is available on PyPI and can be installed with:

```console
$ pip install fasthx
```

The package has optional dependencies for the following **official integrations**:

- [htmy](https://volfpeter.github.io/htmy/): `pip install fasthx[htmy]`.
- [jinja](https://jinja.palletsprojects.com/en/stable/): `pip install fasthx[jinja]`.

## Examples

For complete, but simple examples that showcase the basic use of `FastHX`, please see the [examples](https://github.com/volfpeter/fasthx/tree/main/examples) folder.

### HTMY templating

Requires: `pip install fasthx[htmy]`.

Serving HTML and HTMX requests with [htmy](https://volfpeter.github.io/htmy/) is as easy as creating a `fasthx.htmy.HTMY` instance and using its `hx()` and `page()` decorator methods on your routes.

The example below assumes the existence of an `IndexPage` and a `UserList` `htmy` component. The full working example with the `htmy` components can be found [here](https://github.com/volfpeter/fasthx/tree/main/examples/htmy-rendering).

```python
from datetime import date

from fastapi import FastAPI
from pydantic import BaseModel

from fasthx.htmy import HTMY

# Pydantic model for the application
class User(BaseModel):
    name: str
    birthday: date

# Create the FastAPI application.
app = FastAPI()

# Create the FastHX HTMY instance that renders all route results.
htmy = HTMY()

@app.get("/users")
@htmy.hx(UserList)  # Render the result using the UserList component.
def get_users(rerenders: int = 0) -> list[User]:
    return [
        User(name="John", birthday=date(1940, 10, 9)),
        User(name="Paul", birthday=date(1942, 6, 18)),
        User(name="George", birthday=date(1943, 2, 25)),
        User(name="Ringo", birthday=date(1940, 7, 7)),
    ]

@app.get("/")
@htmy.page(IndexPage)  # Render the index page.
def index() -> None: ...
```

### Jinja2 templating

Requires: `pip install fasthx[jinja]`.

To start serving HTML and HTMX requests, all you need to do is create an instance of `fasthx.Jinja` and use its `hx()` or `page()` methods as decorators on your routes. `hx()` only triggers HTML rendering for HTMX requests, while `page()` unconditionally renders HTML. See the example code below:

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fasthx import Jinja
from pydantic import BaseModel

# Pydantic model of the data the example API is using.
class User(BaseModel):
    first_name: str
    last_name: str

# Create the app.
app = FastAPI()

# Create a FastAPI Jinja2Templates instance and use it to create a
# FastHX Jinja instance that will serve as your decorator.
jinja = Jinja(Jinja2Templates("templates"))

@app.get("/")
@jinja.page("index.html")
def index() -> None:
    ...

@app.get("/user-list")
@jinja.hx("user-list.html")
async def htmx_or_data() -> list[User]:
    return [
        User(first_name="John", last_name="Lennon"),
        User(first_name="Paul", last_name="McCartney"),
        User(first_name="George", last_name="Harrison"),
        User(first_name="Ringo", last_name="Starr"),
    ]

@app.get("/admin-list")
@jinja.hx("user-list.html", no_data=True)
def htmx_only() -> list[User]:
    return [User(first_name="Billy", last_name="Shears")]
```

See the full working example [here](https://github.com/volfpeter/fasthx/tree/main/examples/jinja-rendering).

### Custom templating

Requires: `pip install fasthx`.

If you would like to use a rendering engine without FastHX integration, you can easily build on the `hx()` and `page()` decorators which give you all the functionality you will need. All you need to do is implement the `HTMLRenderer` protocol.

Similarly to the Jinja case, `hx()` only triggers HTML rendering for HTMX requests, while `page()` unconditionally renders HTML. See the example code below:

```python
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fasthx import hx, page

# Create the app.
app = FastAPI()

# Create a dependecy to see that its return value is available in the render function.
def get_random_number() -> int:
    return 4  # Chosen by fair dice roll.

DependsRandomNumber = Annotated[int, Depends(get_random_number)]

# Create the render methods: they must always have these three arguments.
# If you're using static type checkers, the type hint of `result` must match
# the return type annotation of the route on which this render method is used.
def render_index(result: list[dict[str, str]], *, context: dict[str, Any], request: Request) -> str:
    return "<h1>Hello FastHX</h1>"

def render_user_list(result: list[dict[str, str]], *, context: dict[str, Any], request: Request) -> str:
    # The value of the `DependsRandomNumber` dependency is accessible with the same name as in the route.
    random_number = context["random_number"]
    lucky_number = f"<h1>{random_number}</h1>"
    users = "".join(("<ul>", *(f"<li>{u['name']}</li>" for u in result), "</ul>"))
    return f"{lucky_number}\n{users}"

@app.get("/")
@page(render_index)
def index() -> None:
    ...

@app.get("/htmx-or-data")
@hx(render_user_list)
def htmx_or_data(random_number: DependsRandomNumber) -> list[dict[str, str]]:
    return [{"name": "Joe"}]

@app.get("/htmx-only")
@hx(render_user_list, no_data=True)
async def htmx_only(random_number: DependsRandomNumber) -> list[dict[str, str]]:
    return [{"name": "Joe"}]
```

See the full working example [here](https://github.com/volfpeter/fasthx/tree/main/examples/custom-rendering).

### External examples

- [FastAPI-HTMX-Tailwind example](https://github.com/volfpeter/fastapi-htmx-tailwind-example): A complex `Jinja2` example with features like active search, lazy-loading, server-sent events, custom server-side HTMX triggers, dialogs, and TailwindCSS and DaisyUI integration.

## Dependencies

The only dependency of this package is `fastapi`.

## Development

Use `ruff` for linting and formatting, `mypy` for static code analysis, and `pytest` for testing.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

Feel free to ask questions or request new features.

And of course all contributions are welcome, including more documentation, examples, code, and tests.

The goal is to make `fasthx` a well-rounded project that makes even your most complex HTMX use-cases easy to implement.

## Contributors

- [Peter Volf](https://github.com/volfpeter)
- [Hasan Sezer Taşan](https://github.com/hasansezertasan)

## License - MIT

The package is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).

## Thank you

Thank you to [Smart-Now](https://www.smart-now.com/) for supporting the project.

<p align="center">
  <img src="static/smart-now-logo.png" height="42" />
</p>
