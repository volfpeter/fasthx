# HTMY Streaming

This example demonstrates how to use the `StreamingRenderer` from [htmy](https://volfpeter.github.io/htmy/) to stream HTML content to the client.

## HTML streaming

HTML streaming is a powerful technique that allows you to send parts of the HTML response to the client as they become available, rather than waiting for the entire response to be ready. This can significantly improve the perceived performance of your application by reducing the time to first byte (TTFB) and first contentful paint (FCP), and enabling progressive loading of content.

## The application

The application itself will be very simple: a single page that displays a list of items. To demonstrate async HTML streaming, we will create a list item component that simulates a slow operation that takes 1 second to resolve. This way list items will be streamed to the client and appear one by one as they become ready.

First we create an `htmy_streaming_app.py` file, import everything we need, create the FastAPI instance, and an `HTMY` instance with the `StreamingRenderer`:

```python hl_lines="4 12"
import asyncio

from fastapi import FastAPI
from htmy import Component, ComponentType, Context, StreamingRenderer, component, html

from fasthx.htmy import HTMY

# Create the app instance.
app = FastAPI()

# Create the HTMY instance with a streaming renderer.
htmy = HTMY(renderer=StreamingRenderer())
```

Next, we create an async list item component that takes 1 second to resolve:

```python
@component
async def slow_list_item(value: ComponentType, _: Context) -> ComponentType:
    """Async list item component that takes 1 second to resolve."""
    await asyncio.sleep(1)
    return html.li(value)
```

In this example we don't create a dedicated page component. Instead, the FastAPI route simply returns the `htmy` components for the `@htmy.page()` decorator to render. This means we now everything in place, except the FastAPI route itself:

```python hl_lines="2 13 21-24"
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
```

`html.ol(*(slow_list_item(f"Item {i}") for i in range(1, 33)))` creates an ordered list of 32 `slow_list_item` components. They will be sent to the client as they get resolved by the streaming renderer.

## Run your application

You can now run your application using `uvicorn` or `fastapi-cli`:

```bash
uvicorn htmy_streaming_app:app --reload
```

Or with the FastAPI CLI if installed:

```bash
fastapi dev htmy_streaming_app.py
```

Once the server is running, open your browser and navigate to `http://127.0.0.1:8000`. You should see the page loading incrementally, with the list items appearing one by one as they get ready.
