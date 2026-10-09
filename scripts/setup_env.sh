#!/usr/bin/env bash
set -euo pipefail

# Diretório raiz do projeto
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "=== [1/3] Configurando Ambiente Virtual Python (.venv) ==="
if [ ! -d ".venv" ]; then
    echo "Criando .venv em ${REPO_ROOT}/.venv..."
    python3 -m venv .venv
else
    echo ".venv já existente em ${REPO_ROOT}/.venv."
fi

# Ativação do ambiente virtual
source .venv/bin/activate

echo "=== [2/3] Instalando dependências Python ==="
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "=== [3/3] Verificando ferramentas .NET CLI (ilspycmd) ==="
if command -v dotnet >/dev/null 2>&1; then
    if ! dotnet tool list -g | grep -q "ilspycmd"; then
        echo "Instalando ilspycmd globalmente..."
        dotnet tool install -g ilspycmd || true
    else
        echo "ilspycmd já está instalado no ambiente .NET."
    fi
else
    echo "[AVISO] 'dotnet' não encontrado no PATH. ilspycmd requer o .NET SDK."
fi

echo "=== Ambiente configurado com sucesso! ==="
echo "Para ativar o ambiente virtual: source .venv/bin/activate"
