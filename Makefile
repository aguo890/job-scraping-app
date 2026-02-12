PYTHON_CMD ?= python
# Run everything (Dashboard + Scraper) and see logs
run:
	docker-compose up --build

# Alias for run
app:
	docker-compose up --build

# Run everything in the background (silent mode)
up:
	docker-compose up -d --build

# Stop everything
down:
	docker-compose down

# Enter the scraper container (for debugging)
shell:
	docker-compose run --rm scraper /bin/bash

# Clean up docker junk
clean:
	docker-compose down -v
	docker system prune -f

# Smart Push - Reconciles then Commits
push: reconcile-dry
	@echo "✅ Board verified. Running smart push..."
	@$(PYTHON_CMD) scripts/autocommit.py

# Reconcile dry run placeholder
reconcile-dry:
	@echo "Reconciling (dry run)..."
