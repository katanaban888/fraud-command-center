PYTHON ?= python

.PHONY: install seed test api frontend

install:
	$(PYTHON) -m pip install -e ".[dev]"

seed:
	$(PYTHON) -m pipeline.run_pipeline --seed 42

test:
	$(PYTHON) -m pytest

api:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm install && npm run dev
