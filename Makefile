.PHONY: install dev run test lint format build deb clean

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e .
	python3 -m pip install -r requirements-dev.txt

run:
	python3 -m neo_piano

test:
	pytest -v --cov=neo_piano --cov-report=term-missing

lint:
	ruff check src tests
	mypy src

format:
	ruff format src tests
	ruff check --fix src tests

build:
	python3 -m build

deb:
	bash scripts/build_deb.sh

clean:
	rm -rf build dist .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} +

