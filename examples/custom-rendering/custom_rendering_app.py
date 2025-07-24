from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, Response

from fasthx import hx, page

# Create the app.
app = FastAPI()


# Create a dependency to see that its return value is available in the render function.
def get_random_number() -> int:
    return 4  # Chosen by fair dice roll.


DependsRandomNumber = Annotated[int, Depends(get_random_number)]


def render_index(result: Any, *, context: dict[str, Any], request: Request) -> str:
    return "<h1>Hello FastHX</h1>"


# Create the render method: it must always have these three arguments.
# If you're using static type checkers, the type hint of `result` must match the return type
# annotation of the route on which this render method is used.
def render_user_list(result: list[dict[str, str]], *, context: dict[str, Any], request: Request) -> str:
    # The value of the `DependsRandomNumber` dependency is accessible with the same name as in the route.
    random_number = context["random_number"]
    lucky_number = f"<h1>{random_number}</h1>"
    users = "".join(("<ul>", *(f"<li>{u['name']}</li>" for u in result), "</ul>"))
    return f"{lucky_number}\n{users}"


@app.get("/", response_model=None, include_in_schema=False)
@page(render_index)
def index() -> None: ...


@app.get("/htmx-or-data")
@hx(render_user_list)
def htmx_or_data(random_number: DependsRandomNumber, response: Response) -> list[dict[str, str]]:
    response.headers["my-response-header"] = "works"
    return [{"name": "Joe"}]


@app.get("/htmx-only", include_in_schema=False)
@hx(render_user_list, no_data=True)
async def htmx_only(random_number: DependsRandomNumber) -> list[dict[str, str]]:
    return [{"name": "Joe"}]
