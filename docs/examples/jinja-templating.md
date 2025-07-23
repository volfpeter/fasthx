# Jinja Templating

## Basics

To start serving HTML and HTMX requests, all you need to do is create an instance of `fasthx.jinja.Jinja` and use its `hx()` or `page()` methods as decorators on your routes. `hx()` only triggers HTML rendering for HTMX requests, while `page()` unconditionally renders HTML, saving you some boilerplate code. See the example code below:

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fasthx.jinja import ComponentHeader, Jinja
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

## Using `ComponentHeader`

In the basic example, routes always rendered a fixed HTML template. `ComponentHeader` lifts this restriction by letting the client submit the _key_ of the required template, automatically looking up the corresponding template, and of course rendering it.

This can be particularly helpful when multiple templates/UI components require the same data and business logic.

```python
app = FastAPI()
jinja = Jinja(Jinja2Templates("templates"))

@app.get("/profile/{id}")
@jinja.hx(
    ComponentHeader(
        "X-Component",
        {
            "card": "profile/card.jinja",
            "form": "profile/form.jinja",
        },
        default="profile/card.jinja",
    ),
)
def get_user_by_id(id: int) -> User:
    return get_user_from_db(id)
```

Given the example above, if the client submits an `HX-Request` which includes an `X-Component` header, the server will render `profile/card.jinja` if `X-Component`'s value is `"card"`, and `profile/form.jinja` if the value is `"form"`. If the `X-Component` header is missing, the default (`profile/card.jinja`) will be rendered.

If you're tired of repeating `"profile/"`, you can just set `prefix="profile"` in the `hx()` (or `page()`) decorator.
