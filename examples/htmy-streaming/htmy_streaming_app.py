import asyncio

from fastapi import FastAPI
from htmy import Component, ComponentType, Context, StreamingRenderer, component, html

from fasthx.htmy import HTMY

# Create the app instance.
app = FastAPI()

# Create the HTMY instance with a streaming renderer.
htmy = HTMY(renderer=StreamingRenderer())


@component
async def slow_list_item(value: ComponentType, _: Context) -> ComponentType:
    """Async list item component that takes 1 second to resolve."""
    await asyncio.sleep(1)
    return html.li(value)


@app.get("/")
@htmy.page()
def index() -> Component:
    """The index page route."""
    return (
        html.DOCTYPE.html,
        html.html(
            html.head(
                html.title("HTMY Streaming Example"),
                html.Meta.charset(),
                html.Meta.viewport(),
                # Use PicoCSS for styling
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
