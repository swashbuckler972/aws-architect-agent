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
# Éditer .env : renseigner GITHUB_TOKEN, GITHUB_REPO

# 3. Démarrer la stack
make up

# 4. Puller les modèles Ollama (première fois, peut prendre plusieurs minutes)
make pull
# Ou manuellement :
# docker compose exec ollama ollama pull devstral-small-2:24b

# 5. Ouvrir l'interface
open http://localhost:3000
```

## Structure du projet

```
aws-architect-agent/
├── docker-compose.yml         # Stack complète (4 conteneurs)
├── .env.example               # Template de configuration
├── .env                       # Vos secrets (ne pas committer)
├── Makefile                   # Commandes courantes
├── .sources/                  # Fichiers MD de référence (injectés dans les prompts)
│   ├── standards_iac_terraform.md   # Standards IaC Terraform de l'entreprise
│   └── standards_python.md          # Standards Python de l'entreprise
├── repo/                      # Repo Git local cloné (monté dans strands-agent)
└── agent/
    ├── Dockerfile             # Image strands-agent (à builder)
    ├── requirements.txt       # Dépendances Python
    ├── main.py                # Pipeline principal + LLM Router
    └── tools/
        ├── git_tools.py       # @tool Git/GitHub (gitpython + PyGitHub)
        └── validation_tools.py # @tool terraform fmt/validate, KICS
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

### Convention de nommage des fichiers

| Préfixe de fichier          | Agent(s) ciblé(s)                         |
|-----------------------------|-------------------------------------------|
| `standards_iac_*.md`        | Agent IaC (génération Terraform/HCL)      |
| `standards_python*.md`      | Agent IaC (génération code Python)        |
| Tout autre fichier `.md`    | Agent architecte (conception DDD)         |

### Exemples fournis

- `.sources/standards_iac_terraform.md` — structure des modules, nommage, tags obligatoires, sécurité IAM, chiffrement, gestion du state, versions, CI/CD
- `.sources/standards_python.md` — version Python, style (ruff), structure projet, handlers Lambda, logging, tests, sécurité

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
```
