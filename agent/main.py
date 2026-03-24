"""
AWS Architect Agent — Point d'entrée principal
Framework : Strands · LLM : Ollama (API OpenAI-compatible)
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from strands import Agent
from strands.models.openai import OpenAIModel
from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from tools.git_tools import git_commit_and_push, git_create_pull_request, git_read_file
from tools.validation_tools import terraform_fmt, terraform_validate, kics_scan

load_dotenv()

# ─── LLM ROUTER ─────────────────────────────────────────────────────────────
# Modifier les modèles dans .env sans rebuilder l'image

MODEL_ROUTING = {
    "architect_agent": os.getenv("MODEL_ARCHITECT", "devstral-small-2:24b"),
    "iac_agent":       os.getenv("MODEL_IAC",       "devstral-small-2:24b"),
    "report_agent":    os.getenv("MODEL_REPORT",    "devstral-small-2:24b"),
    "executor_agent":  os.getenv("MODEL_EXECUTOR",  "devstral-small-2:24b"),
}

def get_model(agent_name: str) -> OpenAIModel:
    """Retourne un modèle Strands configuré pour Ollama (API OpenAI-compatible)."""
    return OpenAIModel(
        client_args={
            "base_url": f"{os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')}/v1",
            "api_key": "ollama",   # Ollama accepte n'importe quelle valeur
        },
        model_id=MODEL_ROUTING[agent_name],
    )


# ─── SOURCES LOCALES (pattern injection directe anti-hallucination) ──────────

def load_local_sources(
    directory: str = "/app/sources",
    prefix: str = "",
    max_per_file: int = 2000,
) -> str:
    """Charge les fichiers Markdown depuis *directory*.

    Args:
        directory: chemin du répertoire à lire.
        prefix: si fourni, ne charge que les fichiers dont le nom commence par ce préfixe.
        max_per_file: nombre maximal de caractères lus par fichier.

    Returns:
        Contenu concaténé des fichiers trouvés, ou chaîne vide si le répertoire n'existe pas.
    """
    results = []
    source_dir = Path(directory)
    if not source_dir.exists():
        return ""
    for md_file in sorted(source_dir.glob("**/*.md")):
        if prefix and not md_file.name.startswith(prefix):
            continue
        content = md_file.read_text(encoding="utf-8")
        results.append(f"=== {md_file.name} ===\n{content[:max_per_file]}\n")
    return "\n".join(results)


# ─── MCP CLIENTS ─────────────────────────────────────────────────────────────

def make_terraform_mcp() -> MCPClient:
    """Terraform MCP server (HashiCorp) — subprocess stdio."""
    return MCPClient(lambda: stdio_client(StdioServerParameters(
        command="uvx",
        args=["terraform-mcp-server"],
    )))

def make_localstack_mcp() -> MCPClient:
    """LocalStack MCP server — subprocess stdio → LocalStack :4566."""
    return MCPClient(lambda: stdio_client(StdioServerParameters(
        command="uvx",
        args=["localstack-mcp-server"],
        env={
            **os.environ,
            "LOCALSTACK_ENDPOINT": os.getenv("LOCALSTACK_URL", "http://localstack:4566"),
        },
    )))

def make_knowledge_mcp() -> MCPClient:
    """AWS Knowledge MCP server — remote HTTP via fastmcp proxy stdio."""
    return MCPClient(lambda: stdio_client(StdioServerParameters(
        command="uvx",
        args=["fastmcp", "run", "https://knowledge-mcp.global.api.aws"],
    )))


# ─── AGENTS STRANDS ──────────────────────────────────────────────────────────

async def run_architect_agent(user_request: str) -> str:
    """
    Agent 1 — Conçoit l'architecture DDD AWS.
    Outils : AWS Knowledge MCP (doc AWS à jour), sources locales injectées.
    """
    local_sources = load_local_sources()
    system_prompt = f"""Tu es un architecte AWS expert en Domain-Driven Design.
Tu proposes des architectures AWS robustes, sécurisées et économiques.
Tu génères toujours des diagrammes textuels et des tableaux comparatifs /5 par critère.

SOURCES DE RÉFÉRENCE INTERNES :
{local_sources}

CONTEXTE UTILISATEUR : {os.getenv('USER_CONTEXT', '')}
"""
    with make_knowledge_mcp() as knowledge_tools:
        agent = Agent(
            model=get_model("architect_agent"),
            system_prompt=system_prompt,
            tools=[*knowledge_tools.list_tools_sync()],
        )
        result = await agent.run_async(user_request)
        return str(result)


async def run_iac_agent(architecture: str) -> str:
    """
    Agent 2 — Génère l'IaC Terraform et le code Python 3.13+.
    Outils : Terraform MCP (registry + syntaxe HCL), AWS Knowledge MCP.
    Les standards d'entreprise sont injectés depuis /app/sources (fichiers standards_iac_* et standards_python_*).
    """
    iac_standards = load_local_sources(prefix="standards_iac_")
    python_standards = load_local_sources(prefix="standards_python")
    standards_block = ""
    if iac_standards:
        standards_block += f"\nSTANDARDS IaC ENTREPRISE :\n{iac_standards}"
    if python_standards:
        standards_block += f"\nSTANDARDS PYTHON ENTREPRISE :\n{python_standards}"

    with make_terraform_mcp() as tf_tools, make_knowledge_mcp() as knowledge_tools:
        agent = Agent(
            model=get_model("iac_agent"),
            system_prompt=f"""Tu es un expert Terraform et Python 3.13+.
Tu génères du HCL propre, validé et sécurisé (least privilege IAM, chiffrement par défaut).
Tu utilises toujours les dernières versions des providers AWS.
Tu ajoutes des outputs Terraform utiles et des variables paramétrables.
{standards_block}
RÈGLE ABSOLUE : respecte scrupuleusement les standards ci-dessus pour tout le code généré.""",
            tools=[
                *tf_tools.list_tools_sync(),
                *knowledge_tools.list_tools_sync(),
                terraform_fmt,
                terraform_validate,
                kics_scan,
            ],
        )
        result = await agent.run_async(
            f"Génère l'IaC Terraform pour cette architecture :\n\n{architecture}"
        )
        return str(result)


async def run_report_agent(architecture: str, iac_code: str) -> str:
    """
    Agent 3 — Génère le rapport Markdown structuré.
    Outils : git (lecture du repo pour le contexte).
    """
    agent = Agent(
        model=get_model("report_agent"),
        system_prompt="""Tu génères des rapports Markdown professionnels structurés.
Format attendu :
# Rapport — [titre]
## Résumé exécutif
## Architecture proposée (tableau comparatif /5 par critère, TOTAL /25, trié, avec un gagnant)
## Solution recommandée (justification)
## Procédure pas à pas (blocs bash)
## Sources (distinguer local vs web)""",
        tools=[git_read_file],
    )
    result = await agent.run_async(
        f"Génère le rapport pour :\n\nARCHITECTURE:\n{architecture}\n\nIAC:\n{iac_code[:3000]}"
    )
    return str(result)


async def run_executor_agent(iac_code: str) -> str:
    """
    Agent 4 — Valide et déploie sur LocalStack.
    Outils : LocalStack MCP, validation IaC, git commit.
    """
    with make_localstack_mcp() as ls_tools:
        agent = Agent(
            model=get_model("executor_agent"),
            system_prompt="""Tu valides et déploies de l'IaC Terraform sur LocalStack.
Tu analyses les erreurs IAM et proposes des corrections.
Tu commites uniquement le code validé sur GitHub.""",
            tools=[
                *ls_tools.list_tools_sync(),
                terraform_fmt,
                terraform_validate,
                kics_scan,
                git_commit_and_push,
                git_create_pull_request,
            ],
        )
        result = await agent.run_async(
            f"Valide et déploie ce code Terraform sur LocalStack :\n\n{iac_code}"
        )
        return str(result)


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

async def run_pipeline(user_request: str) -> None:
    print(f"\n{'='*60}")
    print(f"DEMANDE : {user_request}")
    print(f"{'='*60}\n")

    print("[1/4] Conception architecture DDD...")
    architecture = await run_architect_agent(user_request)
    print(architecture[:500], "...\n")

    print("[2/4] Génération IaC Terraform...")
    iac_code = await run_iac_agent(architecture)

    print("[3/4] Génération rapport Markdown...")
    report = await run_report_agent(architecture, iac_code)

    # Détection rapport valide (pattern conservé depuis v0.3.0)
    if report.startswith("# Rapport"):
        output_path = Path("/app/output/rapport.md")
        output_path.write_text(report, encoding="utf-8")
        print(f"Rapport écrit dans {output_path}")
    else:
        print("AVERTISSEMENT : rapport non détecté, vérifier la sortie de report_agent")

    print("[4/4] Validation et déploiement LocalStack...")
    validation_result = await run_executor_agent(iac_code)
    print(validation_result[:500])

    print(f"\n{'='*60}")
    print("Pipeline terminé.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    request = os.getenv("USER_REQUEST", "Propose une architecture DDD pour une API REST serverless sur AWS avec Lambda, API Gateway, DynamoDB et S3.")
    asyncio.run(run_pipeline(request))
