# ODG Liguria Workflow Makefile
# Makefile for managing the ODG Liguria Workflow project

# Variables
PYTHON = python3
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
	@echo "  run              Run the main application (PDF processing with deferred scraping)"
	@echo "  run-immediate    Run with immediate scraping (slower but complete)"
	@echo "  check-publication Check publication status of unpublished deliberations"
	@echo "  dashboard        Generate analytics dashboard"
	@echo "  dev              Run in development mode"
	@echo ""
	@echo "Decreto Monitoring:"
	@echo "  monitor-decreto  Monitor decreto publications and sync with Notion"
	@echo "  decreto-status   Show decreto monitoring status"
	@echo "  decreto-force    Force decreto check (ignores timing)"
	@echo "  decreto-setup    Setup decreto monitoring automation"
	@echo "  decreto-scrape   Advanced scraping with REG_AMM extraction"
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
	@echo "  status-extended  Extended status with decreto info"
	@echo ""
	@echo "Special Workflows:"
	@echo "  full-workflow    Complete workflow (PDF + decreto monitoring)"
	@echo "  decreto-watch    Continuous decreto monitoring"
	@echo "  notion-test      Test Notion API connection"
	@echo "  decreto-logs     View decreto monitoring logs"
	@echo "  decreto-clean    Clean decreto temporary files"

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
	@if [ "$(PDF)" ]; then \
		echo "Running ODG Liguria Workflow with PDF: $(PDF)"; \
		$(PYTHON) scripts/cli.py process --pdf "$(PDF)" --scraping-mode deferred --verbose; \
	else \
		echo "Usage: make run PDF=data/input/sample.pdf"; \
		echo "Available PDFs:"; \
		ls -la data/input/*.pdf 2>/dev/null || echo "No PDF files found in data/input/"; \
	fi

.PHONY: run-immediate
run-immediate:
	@if [ "$(PDF)" ]; then \
		echo "Running ODG Liguria Workflow with immediate scraping: $(PDF)"; \
		$(PYTHON) scripts/cli.py process --pdf "$(PDF)" --scraping-mode immediate --verbose; \
	else \
		echo "Usage: make run-immediate PDF=data/input/sample.pdf"; \
		echo "Available PDFs:"; \
		ls -la data/input/*.pdf 2>/dev/null || echo "No PDF files found in data/input/"; \
	fi

.PHONY: check-publication
check-publication:
	@echo "Checking publication status of unpublished deliberations..."
	$(PYTHON) scripts/cli.py check-publication --days 30 --verbose

.PHONY: dashboard
dashboard:
	@echo "Generating analytics dashboard..."
	$(PYTHON) scripts/cli.py dashboard --output dashboard.html --open
	@echo "Dashboard generated and opened in browser!"

.PHONY: dev
dev:
	@echo "Starting in development mode..."
	APP_ENV=development APP_DEBUG=true $(PYTHON) -m $(MAIN_MODULE)

# Testing
.PHONY: test
test:
	@echo "Running all tests..."
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-all
test-all:
	@echo "Running comprehensive test suite..."
	@echo "🧪 Running linting checks..."
	$(PYTHON) -m flake8 src/ scripts/ --max-line-length=100 --extend-ignore=E203,W503
	$(PYTHON) -m black --check src/ scripts/
	$(PYTHON) -m isort --check-only src/ scripts/
	@echo "🧪 Running unit tests..."
	$(PYTHON) -m pytest $(TEST_DIR)/unit -v
	@echo "🧪 Running integration tests..."
	$(PYTHON) -m pytest $(TEST_DIR)/integration -v
	@echo "🧪 Running tests with coverage..."
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing -v
	@echo "🧪 Running security checks..."
	$(PYTHON) -m bandit -r src/ -f text || true
	$(PYTHON) -m safety check || true
	@echo "✅ All tests completed!"

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
verify:
	@echo "🔍 Running complete verification suite..."
	@echo "🔍 Testing connection to external services..."
	$(PYTHON) scripts/cli.py test-connection --detailed
	@echo "🔍 Verifying decreto publication status..."
	$(PYTHON) scripts/cli.py verify --days 30
	@echo "🔍 Running health checks..."
	$(PYTHON) -c "from src.workflow_orchestrator import ODGWorkflowOrchestrator; import os; from dotenv import load_dotenv; load_dotenv(); orch = ODGWorkflowOrchestrator(os.getenv('NOTION_TOKEN'), os.getenv('NOTION_DATABASE_ID'), os.getenv('ANTHROPIC_API_KEY')); print('Health check:', orch.health_check())"
	@echo "🔍 Running linting checks..."
	$(PYTHON) -m flake8 src/ scripts/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "🔍 Running type checking..."
	$(PYTHON) -m mypy src/ --ignore-missing-imports || true
	@echo "🔍 Running tests..."
	$(PYTHON) -m pytest $(TEST_DIR) -v --tb=short
	@echo "🔍 Checking dependencies..."
	$(PIP) check
	@echo "✅ All verification checks completed!"

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

# Decreto Monitoring (New functionality)
.PHONY: monitor-decreto
monitor-decreto:
	@echo "🔍 Monitoring decreto publications with Notion sync..."
	$(PYTHON) decreto_notion_sync.py

.PHONY: decreto-status
decreto-status:
	@echo "📊 Decreto monitoring status:"
	$(PYTHON) decreto_auto_monitor.py status

.PHONY: decreto-force
decreto-force:
	@echo "🔧 Forcing decreto check..."
	$(PYTHON) decreto_auto_monitor.py force

.PHONY: decreto-setup
decreto-setup:
	@echo "🤖 Setting up decreto monitoring automation..."
	@if [ -f "setup_decreto_automation.sh" ]; then \
		chmod +x setup_decreto_automation.sh; \
		./setup_decreto_automation.sh; \
	else \
		echo "setup_decreto_automation.sh not found"; \
	fi

.PHONY: decreto-watch
decreto-watch:
	@echo "👁️  Starting continuous decreto monitoring..."
	@echo "Press Ctrl+C to stop"
	@while true; do \
		$(MAKE) monitor-decreto; \
		echo "⏱️  Next check in 6 hours..."; \
		sleep 21600; \
	done

.PHONY: decreto-logs
decreto-logs:
	@echo "📜 Recent decreto monitoring logs:"
	@if [ -f decreto_monitor.log ]; then \
		tail -20 decreto_monitor.log; \
	else \
		echo "No decreto logs found"; \
	fi

.PHONY: decreto-clean
decreto-clean:
	@echo "🧹 Cleaning decreto monitoring files..."
	@rm -f decreto_sync_report_*.json
	@rm -f daily_summary_*.json
	@rm -f advanced_decreto_search_results_*.json
	@rm -f production_decreto_results_*.json
	@echo "Decreto monitoring files cleaned"

.PHONY: decreto-scrape-advanced
decreto-scrape-advanced:
	@echo "🔍 Running advanced decreto scraping with REG_AMM extraction..."
	$(PYTHON) decreto_scraper_production.py

.PHONY: decreto-test-form
decreto-test-form:
	@echo "🧪 Testing decreto form structure and functionality..."
	@$(PYTHON) -c "from decreto_scraper_production import ProductionDecretoScraper; scraper = ProductionDecretoScraper(); scraper.test_search_functionality()"

.PHONY: decreto-scrape
decreto-scrape:
	@echo "🎯 Running targeted decreto scraping for Notion deliberations..."
	@echo "This will search for REG_AMM attachments and update URL_Decreto field"
	$(PYTHON) decreto_scraper_final_working.py

.PHONY: notion-test
notion-test:
	@echo "🔗 Testing Notion connection..."
	@$(PYTHON) -c "import os; exec('''try:\n    from dotenv import load_dotenv\n    load_dotenv()\n    token = os.getenv('NOTION_TOKEN')\n    db_id = os.getenv('NOTION_DATABASE_ID')\n    if token and db_id and token != 'your_notion_integration_token_here':\n        print('✅ Notion credentials configured')\n        import requests\n        headers = {'Authorization': f'Bearer {token}', 'Notion-Version': '2022-06-28'}\n        resp = requests.get(f'https://api.notion.com/v1/databases/{db_id}', headers=headers, timeout=10)\n        print('✅ Notion connection successful' if resp.status_code == 200 else f'❌ Notion connection failed: {resp.status_code}')\n    else:\n        print('⚠️ Notion credentials not configured in .env')\nexcept Exception as e:\n    print(f'❌ Error testing Notion: {e}')\n''')"

# Complete system workflow
.PHONY: full-workflow
full-workflow:
	@echo "🏛️  Running complete ODG Liguria workflow..."
	@if [ "$(PDF)" ]; then \
		echo "📄 Processing PDF: $(PDF)"; \
		$(MAKE) run PDF=$(PDF); \
		echo "🔍 Checking decreto publications..."; \
		$(MAKE) monitor-decreto; \
		echo "📊 System status:"; \
		$(MAKE) status; \
	else \
		echo "Usage: make full-workflow PDF=data/input/sample.pdf"; \
	fi

# Enhanced status with decreto info
.PHONY: status-extended
status-extended: status
	@echo ""
	@echo "Decreto Monitoring Status:"
	@echo "========================="
	@$(MAKE) decreto-status

# Make sure intermediate files are not deleted
.PRECIOUS: %.py