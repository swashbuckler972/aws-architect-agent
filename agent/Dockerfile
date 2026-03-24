FROM python:3.13-slim

# ─── Évite les prompts interactifs apt ─────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ─── Dépendances système ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ─── Terraform CLI ──────────────────────────────────────────────────────────
# Vérifier la dernière version : https://releases.hashicorp.com/terraform/
ARG TERRAFORM_VERSION=1.9.8
RUN curl -fsSL \
    "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin \
    && rm /tmp/tf.zip \
    && terraform version

# ─── uv (runner Python rapide — requis pour fastmcp et AWS Knowledge MCP) ──
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ─── KICS (Keeping Infrastructure as Code Secure) ──────────────────────────
# Vérifier la dernière version : https://github.com/Checkmarx/kics/releases
ARG KICS_VERSION=2.1.3
RUN curl -fsSL \
    "https://github.com/Checkmarx/kics/releases/download/v${KICS_VERSION}/kics_${KICS_VERSION}_linux_amd64.tar.gz" \
    -o /tmp/kics.tar.gz \
    && tar -xzf /tmp/kics.tar.gz -C /usr/local/bin kics \
    && rm /tmp/kics.tar.gz \
    && kics version

# ─── Répertoire de travail ──────────────────────────────────────────────────
WORKDIR /app

# ─── Dépendances Python ─────────────────────────────────────────────────────
# Copier requirements en premier pour bénéficier du cache Docker layer
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt

# ─── Code applicatif ────────────────────────────────────────────────────────
COPY . .

# ─── Répertoires attendus par l'agent ───────────────────────────────────────
RUN mkdir -p /app/sources /app/repo /app/output

CMD ["python", "main.py"]
