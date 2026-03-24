# Standards IaC Terraform — Entreprise

## Structure des modules

```
modules/
  <nom-service>/
    main.tf        # ressources principales
    variables.tf   # déclaration des variables
    outputs.tf     # valeurs exposées
    versions.tf    # contraintes provider/terraform
    README.md      # description du module
```

## Nommage des ressources

- Format : `{projet}-{environnement}-{service}-{suffixe}`
- Exemples : `myapp-prod-lambda-api`, `myapp-staging-dynamodb-users`
- Variables : snake_case — `var.environment`, `var.project_name`

## Tags obligatoires (toutes les ressources)

```hcl
tags = {
  Project     = var.project_name
  Environment = var.environment
  ManagedBy   = "terraform"
  Owner       = var.team_email
}
```

## Versions

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

## Sécurité IAM

- Least privilege : une politique IAM dédiée par rôle Lambda
- Interdire `*` dans les actions IAM sauf justification explicite
- Activer MFA pour les rôles humains
- Utiliser `aws_iam_policy_document` (data source) plutôt que JSON inline

## Chiffrement

- S3 : `server_side_encryption_configuration` avec AES-256 ou KMS
- DynamoDB : `server_side_encryption { enabled = true }`
- Lambda : variables d'environnement chiffrées via KMS
- Secrets : `aws_secretsmanager_secret`, jamais de secrets dans le code

## Gestion du state

```hcl
terraform {
  backend "s3" {
    bucket         = "myapp-tfstate"
    key            = "${var.environment}/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "myapp-tfstate-lock"
  }
}
```

## CI/CD

- `terraform fmt -check` à chaque PR
- `terraform validate` avant plan
- `tfsec` ou `KICS` scan de sécurité
- Plan en commentaire de PR, apply uniquement sur merge main
