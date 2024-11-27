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

## Dependencies

The only dependency of this package is `fastapi`.

## Development

Use `ruff` for linting and formatting, `mypy` for static code analysis, and `pytest` for testing.

The documentation is built with `mkdocs-material` and `mkdocstrings`.

## Contributing

Feel free to ask questions or request new features.

And of course all contributions are welcome, including more documentation, examples, code, and tests.

The goal is to make `fasthx` a well-rounded project that makes even your most complex HTMX use-cases easy to implement.

## License - MIT

The package is open-sourced under the conditions of the [MIT license](https://choosealicense.com/licenses/mit/).
