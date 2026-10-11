# Mapa arquitetural do Beatstar

Este documento é o índice operacional do repositório. Ele descreve o estado
implementado, não o protocolo completo documentado nas fontes de verdade.

## Mapa de diretórios

| Área | Responsabilidade | Estado |
| --- | --- | --- |
| `server/gateway/` | Transporte HTTP/binário, framing e despacho | runtime |
| `server/handlers/` | Adaptação de comandos do gateway para casos de uso do jogador | runtime |
| `server/gameplay/` | Progressão, placares, brags e multiplayer | runtime/domínio |
| `server/commerce/` | Carteira, catálogo, flags e compras locais | runtime/domínio |
| `server/music/` | Catálogo, charts, assets musicais e Raksha | runtime/domínio |
| `server/assets/` | Ingestão, probes, formatos, armazenamento e waveform | runtime/domínio |
| `server/player_auth/` | Tickets opacos do jogador e política de enforcement | runtime/autenticação |
| `server/admin/` | Sessões administrativas, provisionamento e UI protegida | runtime/autenticação |
| `server/storage/` | Banco legado de jogadores, ORM e migrações | runtime/persistência |
| `server/models/` | Modelos compartilhados; `protocol/` contém modelos gerados | contrato |
| `server/tests/` | Testes de unidade, HTTP, migração e segurança | testes |
| `scripts/` | Decompilação, análise, assets, patching, simulação e E2E Android | pesquisa/operação |
| `client_patch/` | Hooks Frida, configuração de rede e patch de cliente | pesquisa/operação |
| `frontend/` | Painel administrativo Next.js exportado estaticamente | runtime/UI |
| `docs/sot/` | Evidências e contratos observados | fonte de verdade |
| `docs/adr/` | Decisões arquiteturais | governança |
| `docs/plans/` | Planos históricos e propostas ainda não executadas | arquivo |
| `data/`, `decompiled/`, `tools/`, `tmp/`, `.playwright-mcp/` | Dados locais e artefatos de pesquisa | não rastreado |

## Fluxo de dependências

```text
cliente Beatstar
    -> server.api_routes (HTTP gateway/socket, health, configs e bundles)
    -> server.gateway (WireCodec -> HeaderParser -> GatewayDispatcher)
    -> server.handlers
       -> gameplay / commerce / player_auth
       -> storage/player_repository (legado aiosqlite)
       -> music / assets (ORM SQLAlchemy e armazenamento de arquivos)

navegador
    -> /api/admin, /api/commerce, /api/gameplay
    -> server.admin.auth (sessão + CSRF)
    -> routers de domínio
    -> serviços -> repositórios/modelos ORM -> storage/migrations
```

`server/app_factory.py` é o composition root: cria banco, serviços, políticas,
routers e lifespan. `server.app:app` permanece como ponto de entrada compatível
com Uvicorn. Rotas não devem criar conexões ou acessar arquivos diretamente;
essa composição deve continuar concentrada na factory.

## Limites de contrato

- O protocolo em `docs/sot/protocol_specification.md` é a especificação
  documentada. O emulador implementa apenas o subconjunto coberto pelos
  handlers e testes atuais.
- `server/models/protocol/generated_commands.py` é saída de
  `scripts/analyze_protocol.py`. Edite o gerador e regenere; não faça correções
  manuais persistentes no arquivo gerado.
- O gateway HTTP usa envelopes JSON. O socket usa framing binário, mas o
  dispatcher ainda interpreta header e body como JSON; isso não é prova de
  compatibilidade Protobuf/Raksha completa.
- `scripts/simulate_autoplay.py` e chamadas de gameplay sintéticas não são
  validação Android. A validação real exige APK, dispositivo e evidência nos
  checkpoints definidos em `docs/sot/emulator_onboarding_evidence_2026-10-10.md`.
- O export do frontend usa `output: "export"` e `basePath: "/admin"`.
  `server/admin/ui.py` monta `frontend/out` em `/admin`, serve arquivos apenas
  dentro da raiz e aplica fallback HTML somente a rotas sem extensão.

## Convenções de mudança

1. Novos endpoints ficam no router do domínio; autenticação e composição ficam
   em `server/admin/` e `server/app_factory.py`.
2. Schemas de entrada/saída ficam próximos ao domínio (`*_schemas.py`), e
   serviços não importam FastAPI.
3. Migrações são encadeadas em `server/storage/migrations/versions/`; a tabela
   legada `players` continua sob `PlayerRepository` até haver migração explícita.
4. Fixtures pequenas e determinísticas ficam em `server/tests/fixtures/` ou
   `docs/sot/fixtures/` quando representam evidência de pesquisa. Binaries,
   dumps, APKs, capturas e bancos locais não entram no Git.
5. Scripts devem escrever apenas em caminhos fornecidos pela CLI; saídas de
   pesquisa ficam em `decompiled/`, `tmp/`, `dist/` ou `.playwright-mcp/`.
6. Toda mudança de contrato atualiza a fonte de verdade correspondente e um
   teste consumidor. Imports públicos existentes devem permanecer ou ganhar um
   adaptador de compatibilidade durante a migração.

## Validação mínima

```bash
python -m compileall -q server scripts
.venv/bin/python -m pytest server/tests/ -v
(cd frontend && npm run typecheck && npm test)
docker compose config --quiet
git diff --check
```

O conjunto de mídia requer `ffprobe` e `ffmpeg`. Em ambientes sem essas
ferramentas, execute a suíte no contexto `docker-dev` conforme o `README.md` e
registre a indisponibilidade como falha ambiental, não como falha do contrato
de mídia.
