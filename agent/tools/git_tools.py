"""
Outils Git / GitHub — @tool Strands
Remplace le GitHub MCP server Node.js par du Python pur.
Dépendances : gitpython, PyGitHub
"""

import os
from pathlib import Path
from strands import tool


@tool
def git_commit_and_push(file_path: str, content: str, commit_message: str) -> str:
    """
    Écrit un fichier dans le repo local, commit et push sur GitHub.

    Args:
        file_path: chemin relatif dans le repo (ex: 'infra/main.tf')
        content: contenu complet du fichier à écrire
        commit_message: message de commit Git

    Returns:
        URL du commit sur GitHub ou message d'erreur
    """
    try:
        import git
        from github import Github

        repo_path = Path("/app/repo")
        if not repo_path.exists():
            return "ERREUR : /app/repo n'existe pas. Vérifier le volume Docker."

        repo = git.Repo(repo_path)
        full_path = repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        repo.index.add([str(file_path)])
        repo.index.commit(commit_message)
        origin = repo.remotes.origin
        origin.push()

        gh = Github(os.getenv("GITHUB_TOKEN"))
        gh_repo = gh.get_repo(os.getenv("GITHUB_REPO"))
        last_commit = gh_repo.get_commits()[0]
        return f"OK — Commit : {last_commit.html_url}"

    except Exception as e:
        return f"ERREUR git_commit_and_push : {e}"


@tool
def git_create_pull_request(title: str, body: str, head_branch: str) -> str:
    """
    Crée une Pull Request GitHub depuis une branche vers main.

    Args:
        title: titre de la Pull Request
        body: description Markdown de la PR (contexte, changements, tests)
        head_branch: branche source (doit exister sur le remote)

    Returns:
        URL de la PR créée ou message d'erreur
    """
    try:
        from github import Github

        gh = Github(os.getenv("GITHUB_TOKEN"))
        repo = gh.get_repo(os.getenv("GITHUB_REPO"))
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base="main",
        )
        return f"OK — PR #{pr.number} : {pr.html_url}"

    except Exception as e:
        return f"ERREUR git_create_pull_request : {e}"


@tool
def git_read_file(file_path: str) -> str:
    """
    Lit le contenu d'un fichier du repo local.

    Args:
        file_path: chemin relatif dans le repo (ex: 'infra/main.tf')

    Returns:
        Contenu du fichier ou message d'erreur
    """
    try:
        full_path = Path("/app/repo") / file_path
        if not full_path.exists():
            return f"ERREUR : fichier '{file_path}' introuvable dans /app/repo"
        return full_path.read_text(encoding="utf-8")

    except Exception as e:
        return f"ERREUR git_read_file : {e}"


@tool
def git_create_branch(branch_name: str) -> str:
    """
    Crée et checkout une nouvelle branche dans le repo local, puis push.

    Args:
        branch_name: nom de la branche à créer (ex: 'feat/iac-lambda-api')

    Returns:
        Confirmation ou message d'erreur
    """
    try:
        import git

        repo = git.Repo("/app/repo")
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}")
        return f"OK — Branche '{branch_name}' créée et pushée."

    except Exception as e:
        return f"ERREUR git_create_branch : {e}"


@tool
def git_list_files(directory: str = "") -> str:
    """
    Liste les fichiers trackés dans le repo (ou un sous-dossier).

    Args:
        directory: sous-dossier à lister (vide = racine du repo)

    Returns:
        Liste des fichiers ou message d'erreur
    """
    try:
        import git

        repo = git.Repo("/app/repo")
        files = [
            item.a_path for item in repo.index.diff(None)
        ] + repo.untracked_files

        base = Path("/app/repo") / directory
        tracked = [str(p.relative_to("/app/repo")) for p in base.rglob("*") if p.is_file()]
        return "\n".join(tracked) if tracked else "Aucun fichier trouvé."

    except Exception as e:
        return f"ERREUR git_list_files : {e}"
