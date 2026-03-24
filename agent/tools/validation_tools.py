"""
Outils de validation IaC — @tool Strands
terraform fmt · terraform validate · KICS
"""

import subprocess
import tempfile
import os
from pathlib import Path
from strands import tool


def _run(cmd: list[str], cwd: str = None, timeout: int = 60) -> tuple[int, str, str]:
    """Exécute une commande shell et retourne (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


@tool
def terraform_fmt(hcl_code: str) -> str:
    """
    Formate du code HCL Terraform avec 'terraform fmt'.

    Args:
        hcl_code: code HCL brut à formater

    Returns:
        Code HCL formaté ou message d'erreur
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_file = Path(tmpdir) / "main.tf"
            tf_file.write_text(hcl_code, encoding="utf-8")
            rc, stdout, stderr = _run(["terraform", "fmt", str(tf_file)])
            if rc != 0:
                return f"ERREUR terraform fmt :\n{stderr}"
            return tf_file.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERREUR terraform_fmt : {e}"


@tool
def terraform_validate(hcl_code: str) -> str:
    """
    Valide la syntaxe d'un code HCL Terraform avec 'terraform validate'.
    Initialise automatiquement le répertoire avant la validation.

    Args:
        hcl_code: code HCL à valider (un ou plusieurs fichiers en un seul bloc)

    Returns:
        'VALIDE' ou détail des erreurs de validation
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_file = Path(tmpdir) / "main.tf"
            tf_file.write_text(hcl_code, encoding="utf-8")

            # terraform init -backend=false (pas de remote state en validation)
            rc, _, stderr = _run(
                ["terraform", "init", "-backend=false", "-no-color"],
                cwd=tmpdir,
                timeout=120,
            )
            if rc != 0:
                return f"ERREUR terraform init :\n{stderr}"

            rc, stdout, stderr = _run(
                ["terraform", "validate", "-no-color"],
                cwd=tmpdir,
            )
            if rc == 0:
                return f"VALIDE\n{stdout}"
            return f"INVALIDE\n{stdout}\n{stderr}"

    except Exception as e:
        return f"ERREUR terraform_validate : {e}"


@tool
def kics_scan(hcl_code: str) -> str:
    """
    Analyse du code HCL Terraform avec KICS (sécurité et conformité IaC).

    Args:
        hcl_code: code HCL à analyser

    Returns:
        Résumé des findings KICS (HIGH/MEDIUM/LOW/INFO) ou 'AUCUN PROBLÈME DÉTECTÉ'
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_file = Path(tmpdir) / "main.tf"
            tf_file.write_text(hcl_code, encoding="utf-8")
            output_dir = Path(tmpdir) / "kics_results"
            output_dir.mkdir()

            rc, stdout, stderr = _run(
                [
                    "kics", "scan",
                    "--path", tmpdir,
                    "--output-path", str(output_dir),
                    "--output-name", "results",
                    "--report-formats", "json",
                    "--no-color",
                    "--ignore-on-exit", "results",   # ne pas échouer si findings
                ],
                timeout=120,
            )

            results_file = output_dir / "results.json"
            if results_file.exists():
                import json
                data = json.loads(results_file.read_text())
                total = data.get("total_counter", 0)
                if total == 0:
                    return "KICS : AUCUN PROBLÈME DÉTECTÉ"

                summary = [f"KICS : {total} finding(s) détecté(s)\n"]
                for q in data.get("queries", []):
                    severity = q.get("severity", "?")
                    name = q.get("query_name", "?")
                    count = len(q.get("files", []))
                    summary.append(f"  [{severity}] {name} ({count} occurrence(s))")
                return "\n".join(summary)

            return f"KICS : résultats indisponibles\nstdout: {stdout}\nstderr: {stderr}"

    except FileNotFoundError:
        return "ERREUR : KICS non installé dans le conteneur (vérifier le Dockerfile)"
    except Exception as e:
        return f"ERREUR kics_scan : {e}"


@tool
def terraform_plan_localstack(hcl_code: str) -> str:
    """
    Exécute 'terraform plan' contre LocalStack.
    Utilise les variables d'environnement AWS configurées pour LocalStack.

    Args:
        hcl_code: code HCL à planifier

    Returns:
        Sortie du plan Terraform ou message d'erreur
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_file = Path(tmpdir) / "main.tf"
            tf_file.write_text(hcl_code, encoding="utf-8")

            localstack_env = {
                **os.environ,
                "AWS_ACCESS_KEY_ID":     os.getenv("AWS_ACCESS_KEY_ID", "test"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
                "AWS_DEFAULT_REGION":    os.getenv("AWS_DEFAULT_REGION", "eu-west-1"),
                # Override endpoint pour LocalStack
                "TF_VAR_localstack_endpoint": os.getenv("LOCALSTACK_URL", "http://localstack:4566"),
            }

            rc, _, stderr = _run(
                ["terraform", "init", "-backend=false", "-no-color"],
                cwd=tmpdir, timeout=120,
            )
            if rc != 0:
                return f"ERREUR terraform init :\n{stderr}"

            rc, stdout, stderr = _run(
                ["terraform", "plan", "-no-color"],
                cwd=tmpdir, timeout=180,
            )
            if rc == 0:
                return f"PLAN OK\n{stdout}"
            return f"PLAN ERREUR\n{stdout}\n{stderr}"

    except Exception as e:
        return f"ERREUR terraform_plan_localstack : {e}"
