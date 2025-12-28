import asyncio

from fastapi import FastAPI
from htmy import Component, ComponentType, Context, StreamingRenderer, component, html

from fasthx.htmy import HTMY

# -- Components


@component
async def slow_list_item(value: ComponentType, _: Context) -> ComponentType:
    """Async list item component that takes 1 second to resolve."""
    await asyncio.sleep(1)
    return html.li(value)


def index_page(_: None) -> Component:
    """The index page of the application."""
    return (
        html.DOCTYPE.html,
        html.html(
            html.head(
                html.title("HTMY Streaming Example"),
                html.Meta.charset(),
                html.Meta.viewport(),
                html.Link.css("https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"),
            ),
            html.body(
                html.h1("This entire page is being streamed."),
                html.p(
                    "The list items below are asynchronously generated "
                    "and sent to the client as they are ready."
                ),
                html.ol(
                    # Render a number of async list items.
                    *(slow_list_item(f"Item {i}") for i in range(1, 33)),
                ),
                class_="container",
            ),
        ),
    )


# -- Application

# Create the app instance.
app = FastAPI()

# Create the HTMY instance with a streaming renderer.
htmy = HTMY(StreamingRenderer())


@app.get("/")
@htmy.page(index_page)
def index() -> None:
    """The index page route that renders `index_page`."""
    ...
