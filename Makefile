# Memory - Personal Knowledge Base System
# Makefile for common development tasks

# Python version
PYTHON := python3
UV := uv

# Project paths
SRC := src
TESTS := tests

# Color codes
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

.PHONY: help install install-dev install-all sync test test-unit test-integration test-specific \
	lint format typecheck clean coverage run

# Default target
help: ## Show this help message
	@echo ""
	@echo "$(BLUE)Memory - Personal Knowledge Base System$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC)"
	@echo "  make $(YELLOW)<target>$(NC)"
	@echo ""
	@echo "$(GREEN)Installation:$(NC)"
	@echo "  install          Install core dependencies"
	@echo "  install-dev     Install development dependencies"
	@echo "  install-all     Install all dependencies (core + extras)"
	@echo "  sync            Sync dependencies with uv"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-specific   Run specific test file (usage: make test-specific file=tests/unit/test_models.py)"
	@echo "  coverage        Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  lint            Run linters (ruff)"
	@echo "  format          Format code (black)"
	@echo "  typecheck       Run type checker (mypy)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  clean            Clean cache files"
	@echo "  run              Run the CLI application"
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make install-dev"
	@echo "  make test"
	@echo "  make coverage"
	@echo "  make lint && make format && make typecheck"
	@echo ""

# Installation
install: ## Install core dependencies
	@echo "$(GREEN)Installing core dependencies...$(NC)"
	$(UV) sync

install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(UV) sync --extra dev

install-all: ## Install all dependencies (core + extras)
	@echo "$(GREEN)Installing all dependencies...$(NC)"
	$(UV) sync --extra openai --extra chroma

sync: ## Sync dependencies with uv
	@echo "$(GREEN)Syncing dependencies...$(NC)"
	$(UV) sync

# Testing
test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(NC)"
	$(UV) run pytest

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	$(UV) run pytest tests/unit/

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(UV) run pytest tests/integration/

test-specific: ## Run specific test file (usage: make test-specific file=tests/unit/test_models.py)
	@if [ -z "$(file)" ]; then \
		echo "$(YELLOW)Usage: make test-specific file=tests/unit/test_models.py$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running test: $(file)$(NC)"
	$(UV) run pytest $(file)

coverage: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(UV) run pytest --cov=src --cov-report=term-missing --cov-report=html

# Code Quality
lint: ## Run linters (ruff)
	@echo "$(GREEN)Running linter...$(NC)"
	$(UV) run ruff check $(SRC)/

format: ## Format code (black)
	@echo "$(GREEN)Formatting code...$(NC)"
	$(UV) run black $(SRC)/ $(TESTS)/

typecheck: ## Run type checker (mypy)
	@echo "$(GREEN)Running type checker...$(NC)"
	$(UV) run mypy $(SRC)/

# Development
clean: ## Clean cache files
	@echo "$(GREEN)Cleaning cache files...$(NC)"
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

run: ## Run the CLI application
	@echo "$(GREEN)Running Memory CLI...$(NC)"
	$(UV) run memory --help
