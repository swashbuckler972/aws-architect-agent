.PHONY: help up down build pull models logs shell clean run

help:
	@echo "Commandes disponibles :"
	@echo "  make up                        — démarrer la stack complète"
	@echo "  make down                      — arrêter la stack"
	@echo "  make build                     — rebuilder l'image strands-agent"
	@echo "  make pull                      — puller les modèles Ollama configurés dans .env"
	@echo "  make models                    — lister les modèles Ollama disponibles"
	@echo "  make logs                      — suivre les logs de tous les conteneurs"
	@echo "  make shell                     — ouvrir un shell dans strands-agent"
	@echo "  make clean                     — supprimer les volumes Docker (ATTENTION : irréversible)"
	@echo "  make run REQUEST=\"<demande>\"   — lancer le pipeline avec une demande ponctuelle"

up:
	docker compose up -d
	@echo "Open-WebUI disponible sur http://localhost:3000"
	@echo "Ollama disponible sur http://localhost:11434"
	@echo "LocalStack disponible sur http://localhost:4566"

down:
	docker compose down

build:
	docker compose build strands-agent

pull:
	@echo "Pull des modèles Ollama..."
	docker compose exec ollama ollama pull $$(grep MODEL_ARCHITECT .env | cut -d= -f2)
	docker compose exec ollama ollama pull $$(grep MODEL_IAC .env | cut -d= -f2)
	@echo "Done."

models:
	docker compose exec ollama ollama list

logs:
	docker compose logs -f

logs-agent:
	docker compose logs -f strands-agent

shell:
	docker compose exec strands-agent bash

clean:
	@echo "ATTENTION : suppression de tous les volumes Docker !"
	@read -p "Confirmer ? [y/N] " ans && [ "$$ans" = "y" ]
	docker compose down -v

run:
	@if [ -z "$(REQUEST)" ]; then \
		echo "ERREUR : spécifier la demande avec REQUEST=\"...\""; \
		echo "Exemple : make run REQUEST=\"Propose une architecture Lambda + DynamoDB\""; \
		exit 1; \
	fi
	docker compose run --rm -e USER_REQUEST="$(REQUEST)" strands-agent
	@echo ""
	@echo "Rapport disponible dans : output/rapport.md"
