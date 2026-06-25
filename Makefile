.PHONY: sync check lint fmt type imports test cov docs run notebook clean

# Install the workspace + all dependency groups.
sync:
	uv sync --all-groups

# All quality gates (lint, types, layering, tests).
check: lint type imports test

lint:
	uv run ruff check

fmt:
	uv run ruff format
	uv run ruff check --fix

type:
	uv run mypy

imports:
	uv run lint-imports

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing

# Build the documentation site into ./site.
docs:
	uv run mkdocs build

# Reproduce the SK011 accounting workbook from the cached fixture.
run:
	uv run skalar-accounting run --company SK011 \
		--cache apps/cli/fixtures/sk011.json --out build/sk011.xlsx

# Execute the collections->sharing waterfall notebook in place (embeds the figures).
notebook:
	uv run --with nbconvert --with ipykernel python -m nbconvert --to notebook \
		--execute --inplace notebooks/collections_waterfall.ipynb

clean:
	rm -rf site build .pytest_cache .ruff_cache .mypy_cache
