# AWS Architect Agent

Agent IA d'aide au développement et à l'analyse d'architectures AWS.
IaC géré par Terraform · Framework Strands · LLM via Ollama local.

## Prérequis

- Docker Desktop (ou Docker Engine + Compose plugin)
- Git
- 16 Go RAM minimum (pour les modèles Ollama)
- Accès internet (AWS Knowledge MCP server remote)

## Démarrage rapide

```bash
# 1. Cloner le repo
git clone https://github.com/votre-org/aws-architect-agent
cd aws-architect-agent

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env : renseigner GITHUB_TOKEN, GITHUB_REPO, USER_REQUEST

# 3. (Optionnel) Ajouter vos standards d'entreprise
cp -r .sources.example .sources
# Éditer les fichiers dans .sources/ pour les adapter à votre organisation

# 4. Démarrer la stack
make up

# 5. Puller les modèles Ollama (première fois, peut prendre plusieurs minutes)
make pull
# Ou manuellement :
# docker compose exec ollama ollama pull devstral-small-2:24b

# 6. Lancer le pipeline avec votre demande
make run REQUEST="Propose une architecture DDD pour une API REST serverless avec Lambda, API Gateway et DynamoDB"
```

## Utilisation

### Soumettre une demande à l'agent

L'agent exécute un pipeline en 4 étapes (architecture → IaC → rapport → validation).
Pour déclencher le pipeline, deux méthodes sont disponibles :

**Méthode 1 — Variable d'environnement (recommandée)**

Définir `USER_REQUEST` dans `.env`, puis relancer l'agent :

```bash
# Dans .env
USER_REQUEST="Propose une architecture DDD pour une API REST serverless avec Lambda, API Gateway et DynamoDB"

# Relancer le pipeline
docker compose restart strands-agent

# Suivre l'exécution en temps réel
make logs-agent
```

**Méthode 2 — Commande make (sans modifier .env)**

```bash
make run REQUEST="Propose une architecture DDD pour une API REST serverless avec Lambda, API Gateway et DynamoDB"
```

### Consulter les résultats

| Artefact                  | Emplacement              | Description                              |
|---------------------------|--------------------------|------------------------------------------|
| Rapport Markdown          | `./output/rapport.md`    | Rapport structuré généré par l'agent     |
| Code Terraform            | `./repo/infra/`          | IaC généré, formaté et validé            |
| Logs de l'agent           | `make logs-agent`        | Logs temps réel du pipeline              |

```bash
# Lire le rapport généré
cat output/rapport.md

# Ou avec un pager
less output/rapport.md
```

### Exemples de demandes

```
Propose une architecture DDD pour une API REST serverless sur AWS avec Lambda, API Gateway, DynamoDB et S3.

Conçois une architecture de traitement de données en streaming avec Kinesis, Lambda et S3 pour 100k événements/seconde.

Crée une architecture de microservices avec ECS Fargate, ALB, RDS Aurora et ElastiCache pour une application e-commerce.

Propose une solution d'authentification et d'autorisation avec Cognito, API Gateway et Lambda pour une application mobile.
```

### Interface chat Ollama (Open-WebUI)

L'interface Open-WebUI sur `http://localhost:3000` permet de discuter directement avec les modèles Ollama, indépendamment du pipeline agent. Elle est utile pour tester les modèles ou poser des questions ponctuelles sans déclencher le pipeline complet.

## Structure du projet

```
aws-architect-agent/
├── docker-compose.yml             # Stack complète (4 conteneurs)
├── .env.example                   # Template de configuration
├── .env                           # Vos secrets (ne pas committer — gitignored)
├── Makefile                       # Commandes courantes
├── .sources.example/              # Exemples de standards d'entreprise (à copier)
│   ├── standards_iac_terraform.md # Exemple : standards IaC Terraform
│   └── standards_python.md        # Exemple : standards Python
├── .sources/                      # Vos standards réels (gitignored, créer via cp)
│   ├── standards_iac_*.md         # Standards IaC injectés dans iac_agent
│   └── standards_python*.md       # Standards Python injectés dans iac_agent
├── repo/                          # Repo Git local cloné (monté dans strands-agent)
├── output/                        # Rapports générés (rapport.md — gitignored)
└── agent/
    ├── Dockerfile                 # Image strands-agent (à builder)
    ├── requirements.txt           # Dépendances Python
    ├── main.py                    # Pipeline principal + LLM Router
    └── tools/
        ├── git_tools.py           # @tool Git/GitHub (gitpython + PyGitHub)
        └── validation_tools.py    # @tool terraform fmt/validate, KICS
```

## Conteneurs

| Conteneur      | Image                          | Port  | Rôle                          |
|----------------|--------------------------------|-------|-------------------------------|
| `ollama`       | `ollama/ollama:latest`         | 11434 | LLM local                     |
| `open-webui`   | `ghcr.io/open-webui/open-webui`| 3000  | Interface web                 |
| `strands-agent`| Build local (`agent/Dockerfile`)| —    | Agent Strands + outils        |
| `localstack`   | `localstack/localstack:latest` | 4566  | AWS local pour les tests      |

## Serveurs MCP

| Serveur            | Transport    | Localisation                  |
|--------------------|--------------|-------------------------------|
| Terraform MCP      | stdio local  | Subprocess dans strands-agent |
| LocalStack MCP     | stdio local  | Subprocess dans strands-agent |
| AWS Knowledge MCP  | HTTP remote  | `knowledge-mcp.global.api.aws`|

## Ajouter un modèle Ollama

```bash
# Puller le modèle
docker compose exec ollama ollama pull <nom-modele>

# Modifier .env pour l'affecter à un agent
MODEL_ARCHITECT=<nom-modele>

# Redémarrer strands-agent (pas de rebuild nécessaire)
docker compose restart strands-agent
```

## Standards d'entreprise (injection de contexte)

L'agent injecte automatiquement vos standards d'entreprise dans les prompts des agents concernés via le répertoire `.sources/`. Pas besoin de créer des skills dédiés.

### Démarrer depuis les exemples fournis

Le répertoire `.sources.example/` contient des fichiers prêts à l'emploi :

```bash
# Copier les exemples dans .sources/ (gitignored — propre à votre organisation)
cp -r .sources.example .sources

# Adapter les fichiers à vos conventions
# Redémarrer l'agent pour prendre en compte les modifications
docker compose restart strands-agent
```

### Convention de nommage des fichiers

| Préfixe de fichier          | Agent(s) ciblé(s)                         |
|-----------------------------|-------------------------------------------|
| `standards_iac_*.md`        | Agent IaC (génération Terraform/HCL)      |
| `standards_python*.md`      | Agent IaC (génération code Python)        |
| Tout autre fichier `.md`    | Agent architecte (conception DDD)         |

### Exemples fournis dans `.sources.example/`

- `.sources.example/standards_iac_terraform.md` — structure des modules, nommage, tags obligatoires, sécurité IAM, chiffrement, gestion du state, versions, CI/CD
- `.sources.example/standards_python.md` — version Python, style (ruff), structure projet, handlers Lambda, logging, tests, sécurité

### Ajouter vos propres standards

```bash
# Créer un fichier de standards IaC spécifique à votre organisation
cat > .sources/standards_iac_naming.md << 'EOF'
# Convention de nommage interne
...
EOF

# Redémarrer l'agent (aucun rebuild nécessaire, les fichiers sont montés en volume)
docker compose restart strands-agent
```

Les fichiers sont montés en lecture seule dans le conteneur (`/app/sources`) et rechargés à chaque appel d'agent.

## Commandes utiles

```bash
make up            # démarrer
make down          # arrêter
make build         # rebuilder strands-agent après modif Dockerfile/requirements
make logs-agent    # logs de l'agent en temps réel
make shell         # shell interactif dans strands-agent
make run REQUEST="Propose une architecture Lambda + API Gateway + DynamoDB"
                   # lancer le pipeline avec une demande ponctuelle
```
