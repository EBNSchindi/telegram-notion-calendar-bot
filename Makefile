.PHONY: help install test test-unit test-integration lint format type-check dev clean docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run all tests
	pytest

test-unit: ## Run only unit tests
	pytest -m "unit"

test-integration: ## Run only integration tests
	pytest -m "integration"

test-watch: ## Run tests in watch mode
	pytest --tb=short -q --disable-warnings -x

lint: ## Run linter (flake8)
	flake8 src tests

format: ## Format code with black and isort
	black src tests
	isort src tests

format-check: ## Check code formatting
	black --check src tests
	isort --check-only src tests

type-check: ## Run type checker (mypy)
	mypy src

dev: ## Run development setup
	@echo "Setting up development environment..."
	pip install -r requirements.txt
	@echo "Development environment ready!"
	@echo "Don't forget to:"
	@echo "1. Copy .env.example to .env"
	@echo "2. Fill in your API keys"
	@echo "3. Run 'make test' to verify setup"

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

docker-build: ## Build Docker image
	docker-compose build

docker-run: ## Run with Docker Compose
	docker-compose up

docker-dev: ## Run in development mode with Docker
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

run-local: ## Run bot locally (requires .env file)
	python src/bot.py

setup-notion: ## Instructions for Notion setup
	@echo "🔧 Notion Setup Instructions:"
	@echo ""
	@echo "1. Create a Notion integration:"
	@echo "   - Go to https://www.notion.so/my-integrations"
	@echo "   - Click 'New integration'"
	@echo "   - Give it a name and select workspace"
	@echo "   - Copy the 'Internal Integration Token'"
	@echo ""
	@echo "2. Create a calendar database:"
	@echo "   - Create a new page in Notion"
	@echo "   - Add a database with these properties:"
	@echo "     * Title (Title)"
	@echo "     * Date (Date)"
	@echo "     * Description (Text, optional)"
	@echo "     * Created (Date)"
	@echo ""
	@echo "3. Share database with integration:"
	@echo "   - Click 'Share' on your database page"
	@echo "   - Invite your integration"
	@echo ""
	@echo "4. Get database ID:"
	@echo "   - Copy database URL: https://notion.so/workspace/DATABASE_ID?v=..."
	@echo "   - DATABASE_ID is the part before '?v='"
	@echo ""
	@echo "5. Update .env file with NOTION_API_KEY and NOTION_DATABASE_ID"