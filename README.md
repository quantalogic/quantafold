# AI Super Agent

A Python project implementing an AI Super Agent with modern tooling and best practices.

## Setup

This project uses Poetry for dependency management. To get started:

1. Install Poetry if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

## Development

- Run tests: `pytest`
- Format code: `ruff format .`
- Sort imports: `isort .`
- Lint code: `ruff check .`

## Project Structure

```
├── src/
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── pyproject.toml
└── README.md
```
