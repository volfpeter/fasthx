![Tests](https://github.com/volfpeter/fasthx/actions/workflows/tests.yml/badge.svg)
![Linters](https://github.com/volfpeter/fasthx/actions/workflows/linters.yml/badge.svg)
![Documentation](https://github.com/volfpeter/fasthx/actions/workflows/build-docs.yml/badge.svg)
![PyPI package](https://img.shields.io/pypi/v/fasthx?color=%2334D058&label=PyPI%20Package)

**Source code**: [https://github.com/volfpeter/fasthx](https://github.com/volfpeter/fasthx)

**Documentation and examples**: [https://volfpeter.github.io/fasthx](https://volfpeter.github.io/fasthx/)

# FastHX

FastAPI server-side rendering with built-in HTMX support.

## Key features

- **Decorator syntax** that works with FastAPI as one would expect, no need for unused or magic dependencies in routes.
- Built for **HTMX**, but can be used without it.
- Works with **any templating engine** or server-side rendering library, e.g. `htmy`, `jinja2`, or `dominate`.
- Gives the rendering engine **access to all dependencies** of the decorated route.
- HTMX **routes work as expected** if they receive non-HTMX requests, so the same route can serve data and render HTML at the same time.
- **Response headers** you set in your routes are kept after rendering, as you would expect in FastAPI.
- **Correct typing** makes it possible to apply other (typed) decorators to your routes.
- Works with both **sync** and **async routes**.

## Support

Consider supporting the development and maintenance of the project through [sponsoring](https://buymeacoffee.com/volfpeter), or reach out for [consulting](https://www.volfp.com/contact?subject=Consulting%20-%20FastHX) so you can get the most out of the library.

## Installation

The package is available on PyPI and can be installed with:

```console
$ pip install fasthx
```

The package has optional dependencies for the following **official integrations**:

- [htmy](https://volfpeter.github.io/htmy/): `pip install fasthx[htmy]`.
- [jinja](https://jinja.palletsprojects.com/en/stable/): `pip install fasthx[jinja]`.

## Core concepts

The core concept of FastHX is to let FastAPI routes do their usual job of handling the business logic and returning the result, while the FastHX decorators take care of the entire rendering / presentation layer using a declarative, decorator-based approach.

Interally, FastHX decorators always have access to the decorated route's result, all of its arguments (sometimes called the request context), and the current request. Integrations convert these values into data that can be consumed by the used rendering engine (for example `htmy` or `jinja`), run the rendering engine with the selected component (more on this below) and the created data, and return the result to the client. For more details on how data conversion works and how it can be customized, please see the API documentation of the rendering engine integration of your choice.

The `ComponentSelector` abstraction makes it possible to declaratively specify and dynamically select the component that should be used to render the response to a given request. It is also possible to define an "error" `ComponentSelector` that is used if the decorated route raises an exception -- a typical use-case being error rendering for incorrect user input.

## Dependencies

The only dependency of this package is `fastapi`.

## Development

Use `ruff` for linting and formatting, `mypy` for static code analysis, and `pytest` for testing.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

We welcome contributions from the community to help improve the project! Whether you're an experienced developer or just starting out, there are many ways you can contribute:

- **Discuss**: Join our [Discussion Board](https://github.com/volfpeter/fasthx/discussions) to ask questions, share ideas, provide feedback, and engage with the community.
- **Document**: Help improve the documentation by fixing typos, adding examples, and updating guides to make it easier for others to use the project.
- **Develop**: Prototype requested features or pick up issues from the issue tracker.
- **Share**: Share your own project by adding it to the external examples list, helping others discover and benefit from your work.
- **Test**: Write tests to improve coverage and enhance reliability.

## License - MIT

The package is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).
