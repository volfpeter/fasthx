import os

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from fasthx import Jinja


# Pydantic model of the data the example API is using.
class User(BaseModel):
    first_name: str
    last_name: str


basedir = os.path.abspath(os.path.dirname(__file__))

# Create the app instance.
app = FastAPI()

# Create a FastAPI Jinja2Templates instance. This will be used in FastHX Jinja instance.
templates = Jinja2Templates(directory=os.path.join(basedir, "templates"))

# FastHX Jinja instance is initialized with the Jinja2Templates instance.
jinja = Jinja(templates)


@app.get("/user-list")
@jinja.hx("user-list.html")  # Render the response with the user-list.html template.
def htmx_or_data() -> tuple[User, ...]:
    """This route can serve both JSON and HTML, depending on if the request is an HTMX request or not."""
    return (
        User(first_name="Peter", last_name="Volf"),
        User(first_name="Hasan", last_name="Tasan"),
    )


@app.get("/admin-list")
@jinja.hx("user-list.html", no_data=True)  # Render the response with the user-list.html template.
def htmx_only() -> list[User]:
    """This route can only serve HTML, because the no_data parameter is set to True."""
    return [User(first_name="John", last_name="Doe")]


@app.get("/")
@jinja.page("index.html")
def index() -> None:
    """This route serves the index.html template."""
    ...
