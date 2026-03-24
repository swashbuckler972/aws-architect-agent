# Standards Python — Entreprise

## Version

- Python **3.13+** obligatoire
- Type hints sur toutes les fonctions publiques
- `pyproject.toml` pour la configuration des outils

## Style (ruff)

```toml
[tool.ruff]
line-length = 100
target-version = "py313"
select = ["E", "F", "I", "N", "UP", "S", "B"]
```

## Structure projet Lambda

```
functions/
  <nom-handler>/
    handler.py       # point d'entrée Lambda (handler(event, context))
    requirements.txt # dépendances de la fonction
    tests/
      test_handler.py
```

## Handler Lambda

```python
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Point d'entrée Lambda.

    Args:
        event: payload de l'événement (API Gateway, SQS, S3…)
        context: contexte d'exécution Lambda

    Returns:
        Réponse HTTP (statusCode + body) pour API Gateway.
    """
    logger.info("event=%s", json.dumps(event))
    # ... logique métier ...
    return {"statusCode": 200, "body": json.dumps({"message": "OK"})}
```

## Logging

- Utiliser le module `logging` standard (pas `print`)
- Format structuré JSON recommandé en production (`python-json-logger`)
- Ne jamais logger de données sensibles (PII, secrets)

## Tests

- Framework : **pytest**
- Couverture minimale : **80 %**
- Mocks AWS via **moto** ou LocalStack

```python
import pytest
from unittest.mock import patch
from functions.my_handler.handler import handler


def test_handler_returns_200():
    event = {"httpMethod": "GET", "path": "/"}
    result = handler(event, None)
    assert result["statusCode"] == 200
```

## Sécurité

- Valider tous les inputs avec **pydantic** v2
- Secrets via `boto3` + AWS Secrets Manager, jamais dans le code
- Pas de dépendances avec des CVE connues (`pip audit`)
