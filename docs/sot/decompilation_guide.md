# Guia de Descompilação do Beatstar APKM

Este guia detalha o procedimento automatizado e manual para descompilar e inspecionar o pacote Android do Beatstar (`com.spaceapegames.beatstar`).

---

## 1. Pré-Requisitos do Sistema

- **Python 3.10+** (com módulo `venv`)
- **.NET SDK 7.0+** (para Il2CppDumper e ilspycmd)
- **Java OpenJDK 17+** (para JADX e Apktool)

---

## 2. Preparação do Ambiente e Ferramentas

Execute os scripts de configuração inicial na raiz do projeto:

```bash
# 1. Configurar o ambiente virtual Python e ferramentas CLI
./scripts/setup_env.sh

# 2. Baixar e preparar Il2CppDumper, JADX e Apktool
./scripts/setup_tools.sh
```

---

## 3. Execução do Pipeline Automatizado

Para descompilar completamente o arquivo `.apkm` (extração de split APKs, dump do IL2CPP v31, descompilação de assemblies C# com `ilspycmd` e DEX com `jadx`):

```bash
python3 scripts/decompile.py --apkm com.spaceapegames.beatstar_36.1.4.9545-1937149545_2arch_728e926b8a658df508d5be71a65264ec_apkmirror.com.apkm --output-dir decompiled
```

### Argumentos Opcionais:
- `--arch {arm64-v8a,armeabi-v7a}`: Define a arquitetura do `libil2cpp.so` (padrão: `arm64-v8a`).
- `--skip-jadx`: Pula a descompilação Java (foca apenas no C#/Unity).
- `--skip-csharp`: Pula a descompilação com `ilspycmd` (mantém apenas os arquivos de `dump.cs` e `DummyDll/`).

---

## 4. Estrutura dos Artefatos Gerados

Após a execução, os artefatos estarão organizados em `decompiled/`:

- `decompiled/il2cpp/dump.cs`: Declaração completa de classes, atributos, campos e offsets de memória em C#.
- `decompiled/il2cpp/DummyDll/`: Assemblies restaurados prontos para análise no ILSpy, dnSpy ou JetBrains Rider.
- `decompiled/il2cpp/script.json`: Tabela de ponteiros e símbolos para importação no Ghidra / IDA Pro.
- `decompiled/csharp/`: Código fonte descompilado em C# para assemblies essenciais (`SharplaClient`, `SharplaModel`, `SpaceApe.Network`, etc.).
- `decompiled/java/`: Código Android Java descompilado via JADX (`AndroidManifest.xml`, deep links, Firebase).
- `decompiled/assets/`: Arquivos de configuração, JSONs e `boot.config`.

---

## 5. Extração e Análise do Protocolo

Com o `dump.cs` gerado, execute o analisador de protocolo:

```bash
python3 scripts/analyze_protocol.py --dump decompiled/il2cpp/dump.cs
```

O comando produzirá:
- `docs/sot/protocol_commands.json`: Catálogo estruturado de todos os comandos RPC.
- `server/models/protocol/generated_commands.py`: Modelos Pydantic prontos para uso no emulador.
