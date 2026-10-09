#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/tools"
mkdir -p "${TOOLS_DIR}"

echo "=== Configurando Ferramentas de Engenharia Reversa em ${TOOLS_DIR} ==="

# 1. Il2CppDumper
IL2CPP_DIR="${TOOLS_DIR}/Il2CppDumper"
if [ ! -f "${IL2CPP_DIR}/Il2CppDumper.dll" ]; then
    echo "[1/3] Baixando Il2CppDumper v6.7.46..."
    mkdir -p "${IL2CPP_DIR}"
    TMP_ZIP=$(mktemp --suffix=.zip)
    curl -sL "https://github.com/Perfare/Il2CppDumper/releases/download/v6.7.46/Il2CppDumper-net7-v6.7.46.zip" -o "${TMP_ZIP}"
    unzip -qo "${TMP_ZIP}" -d "${IL2CPP_DIR}"
    rm -f "${TMP_ZIP}"
    echo "Il2CppDumper instalado em ${IL2CPP_DIR}."
else
    echo "[1/3] Il2CppDumper já instalado em ${IL2CPP_DIR}."
fi

# 2. JADX
JADX_DIR="${TOOLS_DIR}/jadx"
if [ ! -f "${JADX_DIR}/bin/jadx" ]; then
    echo "[2/3] Baixando JADX v1.5.0..."
    mkdir -p "${JADX_DIR}"
    TMP_ZIP=$(mktemp --suffix=.zip)
    curl -sL "https://github.com/skylot/jadx/releases/download/v1.5.0/jadx-1.5.0.zip" -o "${TMP_ZIP}"
    unzip -qo "${TMP_ZIP}" -d "${JADX_DIR}"
    rm -f "${TMP_ZIP}"
    chmod +x "${JADX_DIR}/bin/jadx"
    echo "JADX instalado em ${JADX_DIR}."
else
    echo "[2/3] JADX já instalado em ${JADX_DIR}."
fi

# 3. Apktool
APKTOOL_DIR="${TOOLS_DIR}/apktool"
if [ ! -f "${APKTOOL_DIR}/apktool.jar" ]; then
    echo "[3/3] Baixando Apktool v2.10.0..."
    mkdir -p "${APKTOOL_DIR}"
    curl -sL "https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar" -o "${APKTOOL_DIR}/apktool.jar"
    echo "Apktool instalado em ${APKTOOL_DIR}/apktool.jar."
else
    echo "[3/3] Apktool já instalado em ${APKTOOL_DIR}/apktool.jar."
fi

echo "=== Todas as ferramentas foram preparadas com sucesso! ==="
