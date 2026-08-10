.PHONY: help up down health logs logs-producer logs-bronze logs-redpanda restart clean test

help:
	@echo "Realtime Streaming Pipeline - Available Commands"
	@echo ""
	@echo "Lifecycle:"
	@echo "  make up               - Start all services (Redpanda, Producer, Bronze)"
	@echo "  make down             - Stop all services"
	@echo "  make restart          - Restart all services"
	@echo "  make clean            - Stop services and delete data volumes"
	@echo ""
	@echo "Monitoring:"
	@echo "  make health           - Check service health"
	@echo "  make logs             - Show logs from all services"
	@echo "  make logs-producer    - Show Producer logs"
	@echo "  make logs-bronze      - Show Bronze consumer logs"
	@echo "  make logs-redpanda    - Show Redpanda logs"
	@echo ""
	@echo "Testing:"
	@echo "  make emit-lmp         - Emit a single LMP tick"
	@echo "  make scenario-1       - Run baseline scenario (10 events)"
	@echo "  make topics           - List Redpanda topics"
	@echo "  make consume          - Consume from market.lmp.raw topic (last 10)"
	@echo ""

up:
	@echo "Starting Realtime Streaming Pipeline..."
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 3
	@make health

down:
	@echo "Stopping services..."
	docker compose down

restart:
	@echo "Restarting services..."
	docker compose restart

clean:
	@echo "Stopping services and removing volumes..."
	docker compose down -v
	@echo "Cleaned."

health:
	@echo ""
	@echo "=== Service Health ==="
	@echo ""
	@echo "Redpanda:"
	@docker exec redpanda curl -s http://localhost:9644/v1/status/ready || echo "NOT READY"
	@echo ""
	@echo "Producer:"
	@docker exec producer curl -s http://localhost:8000/health | python -m json.tool || echo "NOT READY"
	@echo ""
	@echo "Redpanda Topics:"
	@docker exec redpanda rpk topic list || echo "NOT READY"
	@echo ""

logs:
	docker compose logs -f

logs-producer:
	docker compose logs -f producer

logs-bronze:
	docker compose logs -f bronze

logs-redpanda:
	docker compose logs -f redpanda

topics:
	@echo "Redpanda Topics:"
	docker exec redpanda rpk topic list

consume:
	@echo "Consuming from $(KAFKA_TOPIC_LMP) topic (last 10 messages):"
	docker exec redpanda rpk topic consume market.lmp.raw --num 10 --format json

consume-deals:
	@echo "Consuming from $(KAFKA_TOPIC_DEALS) topic (last 10 messages):"
	docker exec redpanda rpk topic consume deal.events --num 10 --format json

# Test scenarios
emit-lmp:
	@echo "Emitting LMP tick..."
	curl -X POST http://localhost:8000/emit/lmp \
		-H "Content-Type: application/json" \
		-d '{"delivery_node": "HB_NORTH", "lmp": 45.50}' | python -m json.tool

emit-deal:
	@echo "Emitting deal event..."
	curl -X POST http://localhost:8000/emit/deal \
		-H "Content-Type: application/json" \
		-d '{"deal_id": "DEAL-001", "event_type": "NEW", "volume_mw": 100.0}' | python -m json.tool

emit-nomination:
	@echo "Emitting nomination..."
	curl -X POST http://localhost:8000/emit/nomination \
		-H "Content-Type: application/json" \
		-d '{"nomination_id": "NOM-001", "deal_id": "DEAL-001", "status": "CONFIRMED"}' | python -m json.tool

scenario-1:
	@echo "Running Baseline Scenario (steady stream of 10 LMP events per node)..."
	curl -X POST http://localhost:8000/scenarios/baseline?count=10 | python -m json.tool
	@echo ""
	@echo "Events emitted. Waiting 2 seconds for Bronze to write..."
	@sleep 2
	@echo ""
	@echo "Checking Redpanda topic:"
	@docker exec redpanda rpk topic consume market.lmp.raw --num 10 --format json | head -30

metrics:
	@echo "Producer Metrics:"
	curl -s http://localhost:8000/metrics | python -m json.tool

shell-producer:
	@echo "Entering Producer container shell..."
	docker exec -it producer /bin/bash

shell-bronze:
	@echo "Entering Bronze container shell..."
	docker exec -it bronze /bin/bash

shell-redpanda:
	@echo "Entering Redpanda container shell..."
	docker exec -it redpanda /bin/bash

# Development helpers
build-producer:
	@echo "Building Producer image..."
	docker build -t producer:local ./producer

build-bronze:
	@echo "Building Bronze image..."
	docker build -t bronze:local ./bronze

build-all: build-producer build-bronze
	@echo "All images built."

ps:
	docker compose ps

.DEFAULT_GOAL := help
