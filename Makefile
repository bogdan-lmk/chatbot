# Makefile
run:
	uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	flake8 src

test:
	pytest