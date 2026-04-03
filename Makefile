.PHONY: help install dev test lint format clean docker-up docker-down k8s-deploy k8s-delete

help:
	@echo "Customer Success Platform - Available Commands"
	@echo "=============================================="
	@echo "install       - Install dependencies"
	@echo "dev           - Run development servers"
	@echo "test          - Run all tests"
	@echo "test-e2e      - Run E2E tests"
	@echo "test-load     - Run load tests"
	@echo "lint          - Run linters"
	@echo "format        - Format code"
	@echo "clean         - Clean build artifacts"
	@echo "docker-up     - Start Docker Compose services"
	@echo "docker-down   - Stop Docker Compose services"
	@echo "k8s-deploy    - Deploy to Kubernetes"
	@echo "k8s-delete    - Delete from Kubernetes"

install:
	pip install -r production/requirements.txt

dev:
	@echo "Starting development servers..."
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	uvicorn production.api.main:app --reload --port 8000

test:
	pytest production/tests/ -v --cov=production --cov-report=html

test-e2e:
	pytest production/tests/test_multichannel_e2e.py -v

test-transition:
	pytest production/tests/test_transition.py -v

test-load:
	locust -f production/tests/load_test.py --host=http://localhost:8000

lint:
	pylint production/
	black --check production/

format:
	black production/
	isort production/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services are ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

k8s-deploy:
	kubectl apply -f production/k8s/namespace.yaml
	kubectl apply -f production/k8s/secrets.yaml
	kubectl apply -f production/k8s/configmap.yaml
	kubectl apply -f production/k8s/deployment-api.yaml
	kubectl apply -f production/k8s/deployment-worker.yaml
	kubectl apply -f production/k8s/service.yaml
	kubectl apply -f production/k8s/ingress.yaml
	kubectl apply -f production/k8s/hpa.yaml
	@echo "Deployment complete!"
	@echo "Check status: kubectl get pods -n customer-success"

k8s-delete:
	kubectl delete namespace customer-success

k8s-status:
	kubectl get all -n customer-success

db-init:
	psql -h localhost -U postgres -d customer_success -f production/database/schema.sql

db-backup:
	pg_dump -h localhost -U postgres customer_success | gzip > backup-$$(date +%Y%m%d-%H%M%S).sql.gz

db-restore:
	@echo "Usage: make db-restore FILE=backup-YYYYMMDD-HHMMSS.sql.gz"
	gunzip < $(FILE) | psql -h localhost -U postgres customer_success
