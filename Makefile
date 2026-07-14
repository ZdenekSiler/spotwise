# Spotwise operations. See docs/deployment.md.
.DEFAULT_GOAL := help
COMPOSE      := docker compose
PROD         := $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml
BACKUP_DIR   := backups
DATE         := $(shell date +%Y-%m-%d-%H%M%S)

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Local stack (docker compose up --build)
	$(COMPOSE) up --build

.PHONY: test
test: ## Run backend tests
	cd backend && uv run pytest -x -q

.PHONY: prod
prod: ## Bring up the production stack (local invocation of the prod override)
	$(PROD) up -d --build --remove-orphans

.PHONY: deploy
deploy: backup ## Deploy: backup -> git pull --ff-only -> prod up -> health check
	git pull --ff-only
	$(PROD) up -d --build --remove-orphans
	@sleep 5 && curl -fsS http://localhost:$${FRONTEND_PORT:-80}/health >/dev/null \
		&& echo "deploy: healthy" || (echo "deploy: health check FAILED"; exit 1)

.PHONY: backup
backup: ## Online SQLite backup out of the backend container
	@mkdir -p $(BACKUP_DIR)
	$(COMPOSE) exec -T backend sh -c "sqlite3 /data/spotwise.db '.backup /tmp/b.db' && cat /tmp/b.db" \
		> $(BACKUP_DIR)/spotwise-$(DATE).db && echo "backup -> $(BACKUP_DIR)/spotwise-$(DATE).db"
	@ls -1t $(BACKUP_DIR)/spotwise-*.db | tail -n +31 | xargs -r rm --

.PHONY: restore
restore: ## Restore a backup: make restore FILE=backups/spotwise-<date>.db
	@test -n "$(FILE)" || (echo "usage: make restore FILE=backups/spotwise-<date>.db"; exit 1)
	cat $(FILE) | $(COMPOSE) exec -T backend sh -c "cat > /tmp/r.db && sqlite3 /data/spotwise.db '.restore /tmp/r.db'"

.PHONY: logs ps shell clean
logs: ## Tail logs
	$(COMPOSE) logs -f --tail=100
ps: ## Show services
	$(COMPOSE) ps
shell: ## Shell into the backend container
	$(COMPOSE) exec backend sh
clean: ## Stop and remove containers (keeps the data volume)
	$(COMPOSE) down
