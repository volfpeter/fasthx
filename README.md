![Tests](https://github.com/volfpeter/fasthx/actions/workflows/tests.yml/badge.svg)
![Linters](https://github.com/volfpeter/fasthx/actions/workflows/linters.yml/badge.svg)
![Documentation](https://github.com/volfpeter/fasthx/actions/workflows/build-docs.yml/badge.svg)
![PyPI package](https://img.shields.io/pypi/v/fasthx?color=%2334D058&label=PyPI%20Package)

**Source code**: [https://github.com/volfpeter/fasthx](https://github.com/volfpeter/fasthx)

**Documentation and examples**: [https://volfpeter.github.io/fasthx](https://volfpeter.github.io/fasthx/)

# FastHX

FastAPI and HTMX, the right way.

Key features:

- **Decorator syntax** that works with FastAPI as one would expect, no need for unused or magic dependencies in routes.
- Works with **any templating engine** or server-side rendering library, e.g. `markyp-html` or `dominate`.
- Built-in **Jinja2 templating support** (even with multiple template folders).
- Gives the rendering engine **access to all dependencies** of the decorated route.
- FastAPI **routes will keep working normally by default** if they receive **non-HTMX** requests, so the same route can serve data and render HTML at the same time.
- **Correct typing** makes it possible to apply other (typed) decorators to your routes.
- Works with both **sync** and **async routes**.

## Installation

The package is available on PyPI and can be installed with:

```console
$ pip install fasthx
```

## Examples

### Jinja2 templating

To start serving HTMX requests, all you need to do is create an instance of `fasthx.Jinja` and use it as a decorator on your routes like this:

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

@app.get("/user-list")
@jinja("user-list.html")
def htmx_or_data() -> list[User]:
    return [
        User(first_name="John", last_name="Lennon"),
        User(first_name="Paul", last_name="McCartney"),
        User(first_name="George", last_name="Harrison"),
        User(first_name="Ringo", last_name="Starr"),
    ]

@app.get("/admin-list")
@jinja.template("user-list.html", no_data=True)
def htmx_only() -> list[User]:
    return [User(first_name="Billy", last_name="Shears")]
```

For full example, see the [examples/template-with-jinja](https://github.com/volfpeter/fasthx/tree/main/examples) folder.

### Custom templating

Custom templating offers more flexibility than the built-in `Jinja` renderer by giving access to all dependencies of the decorated route to the renderer function:

```python
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fasthx import hx

# Create the app.
app = FastAPI()

# Create a dependecy to see that its return value is available in the render function.
def get_random_number() -> int:
    return 4  # Chosen by fair dice roll.

DependsRandomNumber = Annotated[int, Depends(get_random_number)]

# Create the render method: it must always have these three arguments.
# If you're using static type checkers, the type hint of `result` must match the return type
# annotation of the route on which this render method is used.
def render_user_list(result: list[dict[str, str]], *, context: dict[str, Any], request: Request) -> str:
    # The value of the `DependsRandomNumber` dependency is accessible with the same name as in the route.
    random_number = context["random_number"]
    lucky_number = f"<h1>{random_number}</h1>"
    users = "".join(("<ul>", *(f"<li>{u['name']}</li>" for u in result), "</ul>"))
    return f"{lucky_number}\n{users}"

@app.get("/htmx-or-data")
@hx(render_user_list)
def htmx_or_data(random_number: DependsRandomNumber) -> list[dict[str, str]]:
    return [{"name": "Joe"}]

@app.get("/htmx-only")
@hx(render_user_list, no_data=True)
async def htmx_only(random_number: DependsRandomNumber) -> list[dict[str, str]]:
    return [{"name": "Joe"}]

```

## Dependencies

The only dependency of this package is `fastapi`.

## Development

Use `ruff` for linting and formatting, `mypy` for static code analysis, and `pytest` for testing.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

All contributions are welcome.

## Contributors

- [Peter Volf](https://github.com/volfpeter)
- [Hasan Sezer Taşan](https://github.com/hasansezertasan)

## License - MIT

The package is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).
