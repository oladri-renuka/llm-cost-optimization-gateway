.PHONY: help install lint format test test-cov test-failover run-api run-dashboard docker-build docker-run docker-down clean

help:
	@echo "LLM Cost-Optimization Gateway"
	@echo ""
	@echo "Available targets:"
	@echo "  make install          - Install dependencies"
	@echo "  make lint             - Run linter (black, isort, flake8)"
	@echo "  make format           - Auto-format code"
	@echo "  make test             - Run tests with coverage"
	@echo "  make test-cov         - Show coverage report in HTML"
	@echo "  make test-failover    - Run failover tests only"
	@echo "  make run-api          - Start FastAPI server"
	@echo "  make run-dashboard    - Start Gradio dashboard"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-run       - Run in Docker (redis + api)"
	@echo "  make docker-down      - Stop Docker containers"
	@echo "  make clean            - Remove __pycache__, .pyc files"

install:
	pip install -r requirements.txt

lint:
	black --check src/ tests/ --line-length 100
	isort --check-only src/ tests/
	flake8 src/ tests/ --max-line-length 100 --ignore E203,W503

format:
	black src/ tests/ --line-length 100
	isort src/ tests/

test:
	pytest tests/ -v --cov=src/ --cov-report=term-missing --cov-fail-under=80

test-cov:
	pytest tests/ --cov=src/ --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-failover:
	pytest tests/failover/ -v

run-api:
	python -m uvicorn src.api.app:create_app --host 0.0.0.0 --port 8000 --reload --factory

run-dashboard:
	python -m src.ui.dashboard

docker-build:
	docker build -t llm-gateway:latest -f docker/Dockerfile .

docker-run:
	docker-compose -f docker/docker-compose.yml up

docker-down:
	docker-compose -f docker/docker-compose.yml down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
