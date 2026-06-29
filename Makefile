SHELL := /bin/bash

.PHONY: doctor bootstrap backend-deps frontend-deps ensure-deps start stop status test openapi verify-release local

API_PORT ?= 8010
WEB_PORT ?= 5174
API_SESSION := autoresearch-api
WEB_SESSION := autoresearch-web
export PATH := $(HOME)/.local/bin:$(PATH)

local:
	@true

doctor:
	@bash scripts/dev_doctor.sh

bootstrap: backend-deps frontend-deps

backend-deps:
	@bash scripts/dev_doctor.sh --deps-only
	cd backend && uv sync --extra dev

frontend-deps:
	@bash scripts/dev_doctor.sh --deps-only
	cd frontend && npm ci

ensure-deps:
	@if [ ! -d "$(CURDIR)/backend/.venv" ]; then \
		echo "Backend dependency environment missing; running make backend-deps"; \
		$(MAKE) backend-deps; \
	fi
	@if [ ! -d "$(CURDIR)/frontend/node_modules" ]; then \
		echo "Frontend dependencies missing; running make frontend-deps"; \
		$(MAKE) frontend-deps; \
	fi

start: doctor ensure-deps
	@mkdir -p logs
	@if screen -list | grep -q "[.]$(API_SESSION)[[:space:]]"; then \
		echo "API already running in screen: $(API_SESSION)"; \
	else \
		screen -dmS $(API_SESSION) bash -lc 'cd "$(CURDIR)/backend" && uv run python -m uvicorn autoresearch_platform.main:app --host 0.0.0.0 --port $(API_PORT) > "$(CURDIR)/logs/api.log" 2>&1'; \
		echo "API started in screen: $(API_SESSION)"; \
	fi
	@if screen -list | grep -q "[.]$(WEB_SESSION)[[:space:]]"; then \
		echo "Frontend already running in screen: $(WEB_SESSION)"; \
	else \
		screen -dmS $(WEB_SESSION) bash -lc 'cd "$(CURDIR)/frontend" && VITE_API_URL=http://127.0.0.1:$(API_PORT) npm run dev -- --port $(WEB_PORT) > "$(CURDIR)/logs/frontend.log" 2>&1'; \
		echo "Frontend started in screen: $(WEB_SESSION)"; \
	fi
	@bash scripts/wait_for_local_stack.sh $(API_PORT) $(WEB_PORT)

stop:
	@screen -S $(API_SESSION) -X quit 2>/dev/null || true
	@screen -S $(WEB_SESSION) -X quit 2>/dev/null || true
	@lsof -tiTCP:$(API_PORT) -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
	@lsof -tiTCP:$(WEB_PORT) -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
	@rm -f .api.pid .web.pid
	@echo "stopped"

status:
	@curl -fsS http://127.0.0.1:$(API_PORT)/api/v1/system/status || true
	@echo
	@curl -fsS http://127.0.0.1:$(WEB_PORT) >/dev/null && echo "frontend ok" || echo "frontend unavailable"

test: ensure-deps
	cd backend && uv run --extra dev python -m pytest
	cd frontend && npm test

openapi: ensure-deps
	cd backend && uv run python -c "import json; from autoresearch_platform.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > ../docs/openapi.json
	@echo "wrote docs/openapi.json"

verify-release:
	bash scripts/verify_release.sh
