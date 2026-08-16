# =============================================================================
# citebound-01 · el gate vive aqui, no en un documento
# =============================================================================
# `gate-fast` y `gate-full` son TARGETS y no scripts sueltos a proposito
# (constitucion §7.4): el dia que entre pre-commit, invoca el mismo target y no
# cambia una linea.
# =============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help
UV := uv run
COMPOSE := docker compose
OLLAMA_URL ?= http://localhost:11434
OLLAMA_MIN := 0.32.6

.PHONY: help up down warm lint typecheck test-fast test test-int smoke-f0 \
        gate-fast gate-full done eval mutation cov-func secrets clean \
        check-ollama check-r1 openapi ingest golden-sample golden-validate golden-review golden-build \
        clean-mutants

help:  ## esta ayuda
	@grep -hE '^[a-z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | \
	 awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- entorno ---
check-ollama:  ## comprueba que Ollama responde EN EL HOST (R9)
	@curl -sf $(OLLAMA_URL)/api/version >/dev/null || { \
	  echo "Ollama no responde en $(OLLAMA_URL)."; \
	  echo "Corre en el HOST, nunca en compose: Docker en macOS no pasa la GPU (R9)."; \
	  echo "Arrancalo y repite:  ollama serve"; exit 1; }
	@v=$$(curl -sf $(OLLAMA_URL)/api/version | sed 's/.*"version":"\([^"]*\)".*/\1/'); \
	 printf '  ollama %s ' "$$v"; \
	 [ "$$(printf '%s\n%s\n' "$(OLLAMA_MIN)" "$$v" | sort -V | head -1)" = "$(OLLAMA_MIN)" ] \
	   && echo "(>= $(OLLAMA_MIN) ok)" \
	   || { echo "· hace falta >= $(OLLAMA_MIN) (docs/STACK.md). Ejecuta: ollama upgrade"; exit 1; }
# Comparacion >= y no ==, con el motivo escrito: un binario del host que se
# autoactualiza no se puede clavar exacto sin pelearse con quien lo actualiza.
# El pin exacto vive donde si se puede sostener: pyproject.toml y el digest de compose.

up: check-ollama  ## levanta Postgres y espera a que este sano
	$(COMPOSE) up -d --wait
	@echo "  postgres listo en $${CITEBOUND_PG_PORT:-5434}"

down:  ## tumba el entorno, sin volumenes huerfanos
	$(COMPOSE) down --remove-orphans

warm: check-ollama  ## precalienta el modelo. NUNCA dentro de `up`: rompe el cronometro
	@curl -sf $(OLLAMA_URL)/v1/embeddings -H 'Content-Type: application/json' \
	  -d '{"model":"bge-m3","input":["calentando"]}' >/dev/null && echo "  bge-m3 residente"

# ---------------------------------------------------------------- estatica ---
lint:  ## ruff check + format --check
	$(UV) ruff check src tests scripts
	$(UV) ruff format --check src tests scripts

typecheck:  ## mypy --strict sobre [tool.gate].testable, DERIVADO de esa lista
	$(UV) python scripts/typecheck.py

check-r1:  ## R1 · ninguna cita se identifica por el id del troceador
	$(UV) python scripts/check_no_chunk_ids.py

# ------------------------------------------------------------------- tests ---
test-fast:  ## nivel 1 + 1b(dev) + 3. Presupuesto: < 20 s
	$(UV) pytest tests -q -m "not integration" --no-cov

test:  ## todo salvo evals y holdout
	$(UV) pytest tests -q -m "not integration"

test-int:  ## nivel 2, testcontainers. Nunca en el gate rapido
	$(UV) pytest tests -q -m integration --no-cov

# -------------------------------------------------------------------- fase ---
ingest:  ## crea el esquema e indexa el corpus congelado
	$(UV) citebound ingest

smoke-f0:  ## SALIDA DE LA FASE 0 · ingesta + 3 preguntas + >=1 ref que existe
	$(UV) python scripts/smoke_f0.py

openapi:  ## regenera el snapshot de OpenAPI
	$(UV) python -c "import json;from citebound.api.app import openapi;\
	 print(json.dumps(openapi(),ensure_ascii=False,indent=1,sort_keys=True))" \
	 > tests/contract/openapi.snapshot.json
	@echo "  snapshot regenerado; revisa el diff antes de comprometerlo"

# ----------------------------------------------------------------- medidas ---
eval:  ## fase 0: mide G-HALLUC y escribe el informe conforme al contrato
	$(UV) python scripts/eval_f0.py

golden-sample:  ## 1b · elige las 304 preguntas de la cola. Necesita Ollama: deduplica
	$(UV) python -m scripts.golden_sample

golden-review:  ## 1c · LA COLA DE SAMUEL. Una tecla por caso, se reanuda sola
	$(UV) python -m scripts.golden_review

golden-build:  ## 1d · monta v1.jsonl desde la revision de Samuel, con su sha256
	$(UV) python -m scripts.golden_build

golden-validate:  ## SALIDA DE LA FASE 1 · G-GOLDEN-VALID. Necesita Ollama: mide duplicados
	$(UV) python scripts/golden_validate.py

mutation:  ## mutmut sobre [tool.gate].tdd_obligatorio. Solo en `done`
	$(UV) mutmut run

cov-func:  ## un test por funcion publica de [tool.gate].testable
	$(UV) python scripts/check_function_coverage.py

secrets:  ## detect-secrets contra la baseline
	$(UV) detect-secrets scan --baseline .secrets.baseline \
	  --exclude-files 'uv\.lock|tests/recordings/|corpus/raw/|\.snapshot\.json'

# -------------------------------------------------------------------- gate ---
gate-fast: lint typecheck check-r1 test-fast  ## lint + tipos + R1 + suite rapida
	@echo "gate-fast VERDE"

gate-full: gate-fast test test-int check-r1 secrets  ## + integracion y secretos
	@echo "gate-full VERDE"

done:  ## LA UNICA DEFINICION DE HECHO. Uso: make done MILESTONE=0
	@test -n "$(MILESTONE)" || { echo "falta MILESTONE. Uso: make done MILESTONE=0"; exit 2; }
	$(UV) python scripts/done.py --milestone $(MILESTONE)

clean-mutants:  ## tira el arbol y el estado cacheado de mutmut. Obligatorio tras tocar su config
	rm -rf mutants
	@echo "estado de mutmut borrado · el proximo 'make mutation' mide de cero"

clean:  ## borra cachés y el indice derivado
	rm -rf .pytest_cache .ruff_cache .mypy_cache .hypothesis htmlcov coverage.json .coverage
	rm -rf corpus/index
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
