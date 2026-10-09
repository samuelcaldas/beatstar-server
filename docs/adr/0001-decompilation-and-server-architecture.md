# ADR 0001: Pipeline de Descompilação e Arquitetura do Servidor Emulador

- **Data**: 2026-10-09
- **Status**: Aceito
- **Contexto**: O jogo musical Beatstar (Unity 2022.3.50f1 IL2CPP v31) teve seus servidores descontinuados. Precisamos de um pipeline de engenharia reversa reproduzível e um emulador de servidor para preservação e continuidade do jogo.

---

## Decisões

### 1. Pilha de Engenharia Reversa
- **Il2CppDumper (.NET 7/10)**: Escolhido por restaurar completamente as tabelas de tipos C# (`dump.cs`) e gerar assemblies `DummyDll/` fiéis à versão 31 de metadata.
- **ilspycmd (ILSpy CLI)**: Adotado para descompilar os assemblies C# essenciais gerados pelo Il2CppDumper em código legível.
- **JADX CLI**: Utilizado para extrair o código Android Java (`AndroidManifest.xml`, autenticação nativa, integrações externas).
- **Apktool**: Utilizado para injeção de `network-security-config.xml` e reempacotamento de APKs.

### 2. Stack Tecnológica do Servidor Emulador
- **Python (FastAPI + Pydantic v2 + Uvicorn)**:
  - **Motivo**: Permite modelagem rápida e estrita com Pydantic v2, fácil serialização binária/JSON, integração nativa ao ambiente `.venv` e Docker.
  - **Conformidade**: Código estruturado sob princípios SOLID, Object Calisthenics (métodos <= 15 linhas, classes <= 100 linhas, 1 nível de indentação, sem `else`), Fail-Fast e persistência assíncrona SQLite.
- **Fuso Horário Obrigatório**: `America/Sao_Paulo` configurado nas imagens Docker e variáveis de ambiente.

---

## Consequências

- **Positivas**:
  - Pipeline 100% automatizado e idempotente via CLI.
  - Suporte tanto a APK modificado quanto a injeção dinâmica via Frida.
  - Servidor emulador desacoplado, modular e coberto por testes unitários e de integração.
- **Negativas / Desafios**:
  - Arquivos brutos de dump são pesados e exigem controle rigoroso no `.gitignore`.
