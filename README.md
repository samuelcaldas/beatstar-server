# Beatstar Private Server & Reverse Engineering Toolkit

Ambiente completo de engenharia reversa, pipeline de descompilação automatizada e emulador de servidor privado para o jogo musical **Beatstar** (pacote `com.spaceapegames.beatstar`, codinome Space Ape: **Flamingo**).

---

## 🚀 Início Rápido

### 1. Configurar Ambiente Local (.venv e ferramentas)
```bash
# Configura o ambiente virtual Python e dependências
./scripts/setup_env.sh

# Baixa e prepara Il2CppDumper, JADX e Apktool
./scripts/setup_tools.sh
```

### 2. Descompilar o Pacote APKM
```bash
python3 scripts/decompile.py --apkm ../com.spaceapegames.beatstar_36.1.4.9545-1937149545_2arch_728e926b8a658df508d5be71a65264ec_apkmirror.com.apkm --output-dir decompiled
```

### 3. Extrair Comandos do Protocolo de Rede
```bash
python3 scripts/analyze_protocol.py --dump decompiled/il2cpp/dump.cs
```

### 4. Executar o Servidor Emulador Local
```bash
source .venv/bin/activate
uvicorn server.app:app --host 0.0.0.0 --port 8080 --reload
```
Verifique o status em: `http://localhost:8080/health`.

### 5. Executar com Docker Compose
```bash
docker compose up -d --build
```

---

## 🛠️ Conectar o Cliente do Jogo ao Servidor Privado

### Opção A: Modificar e Assinar o APK (Recomendado)
```bash
python3 scripts/patch_apk.py --apk decompiled/extracted/base.apk --output-apk dist/beatstar-patched.apk
adb install dist/beatstar-patched.apk
```

### Opção B: Injeção Dinâmica via Frida (Sem Modificar APK)
```bash
frida -U -f com.spaceapegames.beatstar -l client_patch/frida_hook_network.js
```

---

## 🧪 Executar Testes Automatizados
```bash
source .venv/bin/activate
pytest server/tests/ -v
```

---

## 📚 Documentação Técnica

Consulte o diretório [`docs/`](docs/README.md) para especificações completas:
- [Fonte de Verdade do Protocolo (SOT)](docs/sot/protocol_specification.md)
- [Guia de Descompilação](docs/sot/decompilation_guide.md)
- [Guia de Patch de Cliente](docs/sot/client_patching_guide.md)
- [Referência 1: Beatstar-Script-Android](docs/references/01_beatstar_script_android.md)
- [Referência 2: beatstar-tools](docs/references/02_beatstar_tools.md)
- [ADR 0001: Decisão Arquitetural](docs/adr/0001-decompilation-and-server-architecture.md)
