# Plano de execução: onboarding real e tutorial musical no Beatstar

Plano aprovado: `/home/samuelcaldas/source/repos/beatstar/docs/plans/hashed-jingling-crystal.md`.

## Contexto e objetivo

Comprovar no cliente Android real, contra o servidor local, o percurso de conexão, termos, preferências, seleção de uma das quatro músicas iniciais e conclusão do tutorial com multitouch. Nenhum pagamento, anúncio ou acesso externo real faz parte do primeiro marco. O teste não pode aprovar por chamadas sintéticas, score fixo, estrelas anteriores ou healthcheck isolado. APK repacotado/debug-assinado não será descrito como build debug nativo sem projeto Android fonte.

O código atual tem um validador de gameplay sintético, patcher sem redirecionamento genérico de endpoint e catálogo com duas músicas fictícias. O contrato de música registra playback Android como não comprovado. A branch inclui protótipo de redirect host/porta e listener/codec Protobuf; a avaliação read-only achou potencial de conectividade, porém ainda não há prova de compatibilidade Android/FTUE. O novo listener TCP foi adaptado a `server/app_factory.py` durante o rebase com `main`.

## Task 1: Descobrir alvos, FTUE e viabilidade técnica (M0)

1. Localizar, sem executar conteúdo extraído, APK original, dumps/decompilação, ferramentas, assets e alvos ADB existentes.
2. Consultar guias SoT de decompilação, patch e música. Identificar as quatro músicas iniciais, faixa tutorial, IDs/eventos/telas de FTUE e formato/ligação de assets como evidência observada ou hipótese.
3. Verificar presença e estado do emulador Docker e do servidor, sem iniciar/parar serviços nem instalar APK neste inventário. Determinar caminho de rede real para emulador no Docker e device físico.
4. Delinear prova mínima, reversível, de patch endpoint e carregamento/playback. Não executar se exigir instalação/reset de dispositivo até confirmar os artefatos, rota e serial.

**Expected:** inventário com paths/hashes/versões e estado de ADB; lista de quatro starters com fonte e confiança; matriz de topologia/endpoints; prova de quais pré-requisitos existem. Se APK, assets compatíveis, alvo ou rota estiverem ausentes, registrar o bloqueio e não fingir que o M0 passou.

## Task 2: Pré-flight e redirecionamento de APK (M1)

1. Escrever testes de CLI/validação antes das mudanças: serial obrigatório, endpoint consistente, portas válidas, APK e ferramentas presentes, erro explícito quando uma assinatura de patch não é encontrada ou é incompatível.
2. Corrigir/consolidar o patcher para host e porta explícitos, preservando opções/CLI existentes, usando o patch IL2CPP apenas para versão/assinatura validada. Harmonizar portas do cliente, settings e Compose; não usar host privado hardcoded.
3. Gerar APK de teste repacotado, verificar package/version/signature/config e hash, instalar somente no serial explicitamente pedido e confirmar tráfego recebido pelo servidor local.

**Expected:** testes de patch passam; patch não pode reportar sucesso com zero substituições; APK/rota são verificáveis e correlacionados à execução. Sem toolchain ou APK correspondente, bloquear antes de instalar.

## Task 3: Respostas de servidor para onboarding real (M2)

1. Capturar e comparar requisições/respostas reais do cliente com handlers e SoT.
2. Implementar teste primeiro para catálogo de quatro starters, seleção FTUE e eventos/estado de onboarding com perfil novo e identidade de execução.
3. Implementar apenas os handlers comprovados necessários ao fluxo. Preservar separação HTTP JSON, frames TCP e Protobuf; evitar ack genérico para comandos necessários ao onboarding.
4. Manter IAP/ads inertes e correlacionar estado com o jogador da sessão. Não habilitar enforcement de ticket sem confirmar o eco/uso no tráfego.

**Expected:** testes provam os IDs/mensagens observados, seleção e estado inicial/final; catálogo não usa placeholders como prova de faixa jogável.

## Task 4: Runner UI Android e gameplay real (M3)

1. Criar teste E2E separado de `simulate_autoplay.py` e do runner shell sintético.
2. Automatizar checkpoints de conexão, termos, preferências, quatro faixas, seleção, início e resultado via UIAutomator/acessibilidade. Capturar screenshots e texto/OCR com timestamp/confiança; estado ilegível é fail/inconclusivo.
3. Coletar logcat antes da Activity, confirmar eventos de rede do cliente ao servidor, iniciar e manter playback; executar múltiplos ponteiros simultâneos sincronizados com o chart/tutorial observado.
4. Comparar progresso do perfil novo antes/depois. Uma auditoria sem tela de conclusão, toque sequencial, crash, resultado fixo ou perfil antigo reprova.

**Expected:** pass exige checkpoints UI e estado de servidor coerentes, multitouch demonstrado e tela final observada. Bloqueio de codec/asset/UI deve produzir inconclusivo, nunca pass.

## Task 5: Evidência, documentação e validação (M4/M5)

1. Guardar screenshots em `.playwright-mcp/` e gerar manifesto de execução sem segredos: alvo/serial/rota, APK e hash, checkpoints, texto, ações, tráfego, estado inicial/final e logcat.
2. Documentar comandos para Docker emulator e device físico, limitações de debug signing, pré-requisitos, formatos e evidência disponível. Atualizar índice/docs SoT e remover links `file://` de outros checkouts quando tocar esses docs.
3. Executar testes focados, suíte completa no container `docker-dev`, `compileall`, validação Compose e E2E real por alvo disponível. Não declarar portabilidade para alvo não testado.

**Expected:** documentação reproduzível e resultados explicitam todos os skips/bloqueios. Testes HTTP/unitários não são prova do tutorial no cliente.

## Interfaces e dependências

- Task 1 produz IDs/fontes, artefatos/APK, versão e topologia, consumidos por Tasks 2–4.
- Task 2 produz endpoint verificável e APK identificado, consumidos por Task 4.
- Task 3 produz catálogo/eventos reais, consumidos por Task 4.
- Task 4 produz evidências e estados, documentados em Task 5.

## Validação padrão

Usar `docker --context docker-dev build -t beatstar-dev .`, depois comandos de teste em container descartável sem mount do banco de desenvolvimento. Validar com `python -m pytest server/tests/ -v`, `python -m compileall -q server scripts` e `docker --context docker-dev compose config --quiet`. O E2E Android só passa quando o gameplay nativo e a conclusão forem observados diretamente.
