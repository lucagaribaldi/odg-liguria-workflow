# ODG Liguria Workflow Makefile
# Makefile for managing the ODG Liguria Workflow project

# Variables
PYTHON = python
PIP = pip
VENV = venv
VENV_BIN = $(VENV)/bin
REQUIREMENTS = requirements.txt
SRC_DIR = src
TEST_DIR = tests
MAIN_MODULE = $(SRC_DIR).main
DASHBOARD_MODULE = $(SRC_DIR).dashboard.app

# Default target
.PHONY: help
help:
	@echo "ODG Liguria Workflow - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install all dependencies"
	@echo "  setup            Complete environment setup"
	@echo "  clean            Clean temporary files and caches"
	@echo ""
	@echo "Development:"
	@echo "  run              Run the main application"
	@echo "  dashboard        Start the web dashboard"
	@echo "  dev              Run in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code using black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  pre-commit       Run pre-commit hooks"
	@echo ""
	@echo "Verification:"
	@echo "  verify           Run complete verification suite"
	@echo "  check-deps       Check for dependency issues"
	@echo "  check-config     Validate configuration files"
	@echo ""
	@echo "Database:"
	@echo "  init-db          Initialize database"
	@echo "  reset-db         Reset database (WARNING: deletes data)"
	@echo "  backup-db        Create database backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  backup           Create full system backup"
	@echo "  logs             View recent logs"
	@echo "  status           Show system status"

# Setup and Installation
.PHONY: install
install:
	@echo "Installing dependencies..."
	$(PIP) install -r $(REQUIREMENTS)
	@echo "Dependencies installed successfully!"

.PHONY: setup
setup: install init-db
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file from template"; fi
	@if [ ! -f config.yaml ]; then cp config.yaml.example config.yaml; echo "Created config.yaml from template"; fi
	@mkdir -p logs data/input data/output data/backups cache temp
	@echo "Environment setup completed!"
	@echo "Please edit .env and config.yaml with your settings"

.PHONY: clean
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name "*.tmp" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf temp/*
	rm -rf cache/*
	@echo "Cleanup completed!"

# Development
.PHONY: run
run:
	@echo "Starting ODG Liguria Workflow..."
	$(PYTHON) -m $(MAIN_MODULE)

.PHONY: dashboard
dashboard:
	@echo "Starting web dashboard..."
	$(PYTHON) -m $(DASHBOARD_MODULE)

.PHONY: dev
dev:
	@echo "Starting in development mode..."
	APP_ENV=development APP_DEBUG=true $(PYTHON) -m $(MAIN_MODULE)

# Testing
.PHONY: test
test:
	@echo "Running all tests..."
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing -v

.PHONY: test-unit
test-unit:
	@echo "Running unit tests..."
	$(PYTHON) -m pytest $(TEST_DIR)/unit -v

.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	$(PYTHON) -m pytest $(TEST_DIR)/integration -v

# Code Quality
.PHONY: lint
lint:
	@echo "Running linting checks..."
	$(PYTHON) -m flake8 $(SRC_DIR) $(TEST_DIR)
	@echo "Linting completed!"

.PHONY: format
format:
	@echo "Formatting code..."
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)
	@echo "Code formatted!"

.PHONY: type-check
type-check:
	@echo "Running type checking..."
	$(PYTHON) -m mypy $(SRC_DIR)

.PHONY: pre-commit
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Verification
.PHONY: verify
verify: lint type-check test check-deps check-config
	@echo "All verification checks passed!"

.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	$(PIP) check
	@echo "Dependencies check completed!"

.PHONY: check-config
check-config:
	@echo "Validating configuration..."
	$(PYTHON) -m $(SRC_DIR).utils.config_validator
	@echo "Configuration validation completed!"

# Database
.PHONY: init-db
init-db:
	@echo "Initializing database..."
	$(PYTHON) -m $(SRC_DIR).database.init_db
	@echo "Database initialized!"

.PHONY: reset-db
reset-db:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		$(PYTHON) -m $(SRC_DIR).database.init_db --reset; \
		echo "Database reset completed!"; \
	else \
		echo ""; \
		echo "Database reset cancelled."; \
	fi

.PHONY: backup-db
backup-db:
	@echo "Creating database backup..."
	$(PYTHON) -m $(SRC_DIR).database.backup
	@echo "Database backup completed!"

# Maintenance
.PHONY: backup
backup:
	@echo "Creating full system backup..."
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	backup_dir="backups/system_backup_$$timestamp"; \
	mkdir -p $$backup_dir; \
	cp -r data $$backup_dir/; \
	cp -r logs $$backup_dir/; \
	cp config.yaml $$backup_dir/ 2>/dev/null || true; \
	cp .env $$backup_dir/ 2>/dev/null || true; \
	echo "System backup created in $$backup_dir"

.PHONY: logs
logs:
	@echo "Recent logs:"
	@tail -n 50 logs/odg_workflow.log 2>/dev/null || echo "No logs found"

.PHONY: status
status:
	@echo "System Status:"
	@echo "=============="
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Working directory: $$(pwd)"
	@echo "Configuration file: $$(if [ -f config.yaml ]; then echo 'Present'; else echo 'Missing'; fi)"
	@echo "Environment file: $$(if [ -f .env ]; then echo 'Present'; else echo 'Missing'; fi)"
	@echo "Database: $$(if [ -f data/odg_workflow.db ]; then echo 'Present'; else echo 'Missing'; fi)"
	@echo "Log file: $$(if [ -f logs/odg_workflow.log ]; then echo 'Present (size: $$(stat -f%z logs/odg_workflow.log 2>/dev/null || stat -c%s logs/odg_workflow.log 2>/dev/null) bytes)'; else echo 'Missing'; fi)"
	@echo "Virtual environment: $$(if [ -d $(VENV) ]; then echo 'Present'; else echo 'Missing'; fi)"

# Docker (if needed)
.PHONY: docker-build
docker-build:
	@echo "Building Docker image..."
	docker build -t odg-liguria-workflow .

.PHONY: docker-run
docker-run:
	@echo "Running Docker container..."
	docker run -it --rm -v $$(pwd)/data:/app/data -v $$(pwd)/logs:/app/logs -p 5000:5000 odg-liguria-workflow

# Development utilities
.PHONY: install-dev
install-dev: install
	@echo "Installing development dependencies..."
	$(PIP) install pre-commit pytest-watch
	pre-commit install

.PHONY: watch-tests
watch-tests:
	@echo "Watching for changes and running tests..."
	$(PYTHON) -m pytest_watch $(TEST_DIR)

.PHONY: docs
docs:
	@echo "Generating documentation..."
	@if [ -d docs ]; then \
		cd docs && $(PYTHON) -m sphinx.cmd.build -b html . _build/html; \
	else \
		echo "Documentation directory not found"; \
	fi

# Make sure intermediate files are not deleted
.PRECIOUS: %.py