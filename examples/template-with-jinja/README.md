# Example with Jinja2 Template Engine

## Clone the repo

```shell
git clone https://github.com/volfpeter/fasthx.git
cd fasthx
```

## Install dependencies with virtualenv

- Create and activate a virtual environment:

```shell
python3 -m venv env
source env/bin/activate
```

- Install requirements:

```shell
pip install -r 'examples/template-with-jinja/requirements.txt'
```

> To install current version of `fasthx`, run `pip install -e .`.

## Install dependencies with poetry

```shell
poetry shell
poetry install
```

## Run the application

```shell
uvicorn examples.template-with-jinja.main:app
```
