# Development commands for client-server demo

# Default recipe - show available commands
default:
    @just --list

# Python/Server commands
# ======================

# Install Python dependencies
py-install:
    cd server && uv sync --extra dev

# Run Python linter (ruff)
py-lint:
    cd server && uv run ruff check .

# Fix Python linting issues
py-lint-fix:
    cd server && uv run ruff check --fix .

# Format Python code
py-format:
    cd server && uv run ruff format .

# Run Python type checking
py-typecheck:
    cd server && uv run mypy .

# Run Python tests
py-test:
    cd server && uv run pytest

# Run Python tests with coverage
py-test-coverage:
    cd server && uv run pytest --cov=app --cov-report=html

# Run Python server in development mode
py-server:
    cd server && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
py-migrate:
    cd server && uv run alembic upgrade head

# TypeScript/Console commands
# ===========================

# Install Node.js dependencies for console
console-install:
    cd console && bun install

# Run console in development mode
console-dev:
    cd console && bun run dev

# Build console for production
console-build:
    cd console && bun run build

# Lint console TypeScript
console-lint:
    cd console && bun run lint

# Fix console linting issues
console-lint-fix:
    cd console && bun run lint --fix

# Type check console
console-typecheck:
    cd console && bun run typecheck

# SDK commands
# ============

# Install SDK dependencies
sdk-install:
    cd sdk-ts && bun install

# Build SDK
sdk-build:
    cd sdk-ts && bun run build

# Lint SDK
sdk-lint:
    cd sdk-ts && bun run lint

# Type check SDK
sdk-typecheck:
    cd sdk-ts && bun run typecheck

# Combined commands
# =================

# Install all dependencies
install:
    just py-install
    just console-install
    just sdk-install

# Lint all code
lint:
    just py-lint
    just console-lint
    just sdk-lint

# Type check all code
typecheck:
    just py-typecheck
    just console-typecheck
    just sdk-typecheck

# Format all code
format:
    just py-format

# Run all tests
test:
    just py-test

# Full CI check (lint, typecheck, test)
ci:
    just lint
    just typecheck
    just test

# Development workflow
# ===================

# Start development servers
dev:
    #!/usr/bin/env bash
    echo "Starting Python server..."
    cd server && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    echo "Starting Next.js console..."
    cd console && bun run dev &
    echo "Both servers started. Press Ctrl+C to stop."
    wait

# Clean all build artifacts
clean:
    rm -rf console/.next/
    rm -rf sdk-ts/dist/
    find . -name "__pycache__" -type d -exec rm -rf {} +
    find . -name "*.pyc" -delete

# Docker commands
# ===============

# Build Docker image for server
docker-build:
    docker build -t client-server-demo-api ./server

# Run server in Docker
docker-run:
    docker run -p 8000:8000 client-server-demo-api

# API validation
# ==============

# Validate OpenAPI spec
api-validate:
    cd api && spectral lint openapi.yaml