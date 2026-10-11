# Plano: onboarding real e tutorial musical no Beatstar

## Contexto

O objetivo é documentar o comportamento do cliente real e comprovar, sem falsos positivos, o percurso inicial até executar o tutorial de uma das quatro músicas iniciais contra o servidor local. O primeiro marco cobre conexão, aceitação dos termos, preferências iniciais, seleção de faixa e conclusão observável do tutorial. Autenticação aprofundada, compras, anúncios, downloads gerais e demais comportamentos do cliente ficam como frentes posteriores; não haverá transações, anúncios ou chamadas externas reais nesta fase.

O validador atual não comprova gameplay: `scripts/validate_emulator_song.py` executa cinco taps sequenciais, chama um runner que envia tráfego sintético e aceita estrelas que podem ser anteriores. O patcher `scripts/patch_apk.py` habilita cleartext e assina o APK, mas não configura genericamente o host/porta do gateway. O servidor oferece duas faixas fictícias em `server/handlers/songs_handler.py`; a seleção FTUE não tem fluxo runtime dedicado identificado. O contrato `docs/sot/music_asset_contract.md` declara playback Android bloqueado e lista a faixa tutorial 710/beatmap 660 como candidata não vinculada, não como pacote comprovado.

O usuário priorizou o E2E do tutorial. Como não foi localizado projeto Android/Gradle, a saída de APK prevista é um APK repacotado e debug-assinado com coleta ADB/logcat; isso não será chamado de build Android debug genuíno ou reproduzível. O teste deve falhar ou retornar inconclusivo se não conseguir provar as etapas reais no cliente.

## Abordagem recomendada

Implementar primeiro um caminho fail-fast de pré-flight e prova de conectividade/compatibilidade. Só depois de demonstrados o redirecionamento do endpoint, o carregamento de asset compatível e o início de playback, automatizar onboarding e tutorial. Reutilizar o patcher, runner ADB e servidor existentes onde possível, mas separar rigorosamente simulação de protocolo de E2E no cliente. Não mascarar limitações de formato/protocolo com score fixo, audit fabricado, resultado preexistente ou sucesso de healthcheck.

## Etapas de implementação

1. **Inventário de evidências e pré-requisitos**
   - Ler decompilação/metadata para identificar as quatro faixas iniciais, eventos/telas de onboarding, IDs e sequências de interação do tutorial. Distinguir achados confirmados de hipóteses e atualizar as SoT relevantes.
   - Confirmar, em probe curto, se o cliente pode ser repacotado, instalado e redirecionado para um endpoint configurável; confirmar também se consegue baixar/carregar um asset conhecido e iniciar playback.
   - Encerrar com bloqueio explícito antes da automação visual se endpoint, protocolo, asset ou playback não funcionar. Usar os procedimentos restritos documentados para inspeção de assets; não tratar extração offline como prova de compatibilidade Android.

2. **Contrato de execução determinístico**
   - Definir uma CLI/configuração comum que exija alvo, serial ADB explícito, URL do servidor, APK de origem/saída, pasta de artefatos e identidade nova por execução. Não selecionar dispositivo silenciosamente.
   - Validar ferramentas, package/version/assinatura do APK, disponibilidade do alvo, rota até o servidor e `/health` antes de instalar.
   - Diferenciar emulador Android conectado ao host, emulador executado em Docker e dispositivo físico. Testar a topologia real do container; usar `10.0.2.2` somente quando aplicável. Para aparelho físico usar `adb -s <serial>` e `adb reverse` ou endereço LAN roteável, registrando a rota escolhida. O `--url` deve ser a fonte consistente de endpoint em todas as fases.
   - Garantir idempotência usando perfil de teste novo/isolado e estado inicial consultado. Nunca inferir sucesso de estrelas/progresso antigos nem apagar dados alheios ao teste.

3. **APK de teste e endpoint**
   - Estender `scripts/patch_apk.py` e `client_patch/` para receber endpoint e identidade de teste configuráveis sem depender do IP/Cinta hardcoded no hook Frida.
   - Verificar a configuração efetiva no APK final, assinatura e instalação no serial pedido; calcular hash e registrar versão/package/endpoint no relatório. Se o mecanismo de redirecionamento não puder ser verificado, interromper.
   - Reutilizar a assinatura debug disponível para o pacote repacotado. Descrever corretamente o artefato; build debug real só pode ser oferecido se for encontrado código-fonte e pipeline Android verificável.

4. **Servidor suficiente para o onboarding**
   - Substituir catálogo fake para o percurso de teste por quatro starters confirmados na investigação; IDs, metadados, assets e respostas devem corresponder ao protocolo observado.
   - Implementar/confirmar eventos de termos, preferências, escolha FTUE, início e conclusão conforme as chamadas reais capturadas. Correlacionar eventos e estado final com identidade/ID de execução novos.
   - Confirmar autenticação/ticket pelo tráfego real antes de exigir validação mais estrita, pois o dispatcher atual não valida tickets subsequentes. Não modificar comportamento de segurança como hipótese sem evidência.
   - Manter monetização e integrações externas inertes/isoladas. Não usar rotas de comércio abertas como parte do fluxo de gameplay.

5. **Runner E2E Android com checkpoints reais**
   - Separar o novo teste dos scripts de simulação existentes. Conduzir o APK real por conexão, termos, preferências, listagem das quatro faixas, seleção, início, tutorial e resultado.
   - Preferir UIAutomator/hierarquia de acessibilidade; usar screenshots e OCR como evidência complementar ou fallback explícito. Ler e salvar textos de tela com timestamp e confiança; leitura ambígua é falha/inconclusivo.
   - Implementar multitouch com múltiplos ponteiros simultâneos e sincronização com tutorial/chart observado. Cinco taps sequenciais não satisfazem o aceite. Se precisar de `sendevent`, documentar calibração e validar separadamente em cada dispositivo; não alegar portabilidade não testada.
   - Iniciar coleta de `logcat` antes do app e encerrá-la ao final, guardando crashes/erros filtrados pelo package e contexto suficiente para diagnóstico.

6. **Evidências, teste e documentação**
   - Guardar screenshots somente em `.playwright-mcp/`; junto deles, gerar relatório por execução com serial/alvo/rota, hashes do APK, etapas, textos/hierarquia, leituras OCR/confiança, ações, requisições do cliente observadas no servidor, estado inicial/final e logcat. Evitar credenciais e dados pessoais desnecessários.
   - Criar testes unitários para resolução de endpoint, validação de checkpoint, identidade limpa, política de estados pass/fail/inconclusivo e idempotência. Manter testes de protocolo separados do E2E Android.
   - Atualizar `docs/README.md`, guia de patch/conexão e contrato musical com comandos, pré-requisitos, limites, matriz de alvos e evidências. Trocar links `file://` de outro checkout por referências relativas quando esses arquivos forem tocados.

## Critérios de aceite — sem falsos positivos

Um E2E só passa se, na mesma execução isolada:

- o APK patched instalado no serial especificado efetivamente se comunica com o servidor local configurado;
- a UI confirma termos e preferências e apresenta exatamente os quatro starters identificados;
- a faixa selecionada pertence a esse conjunto e a seleção correspondente aparece no tráfego/estado do servidor;
- o cliente entra em playback, recebe interação multitouch real e chega à tela de conclusão observada;
- mudanças de progresso/audit estão vinculadas ao perfil novo e à execução, com estado inicial/final comparado;
- screenshots, textos/estados, logs e relatório estão completos, e não há crash/falha fatal no logcat.

`/health`, audit isolado, alteração de perfil sem tela de conclusão, texto OCR incerto, score fixo ou progresso anterior nunca são suficientes. Se um checkpoint não puder ser observado, o resultado é inconclusivo ou falho — jamais sucesso. Repetir após reset deve produzir o mesmo fluxo; executar com progresso antigo não pode aprovar o teste.

## Marcos e verificação

- **M0 — Descoberta e viabilidade:** IDs/eventos de onboarding e starters identificados; APK redirecionável e faixa compatível carregada. Bloqueios registrados com logs e requisições observadas.
- **M1 — Pré-flight e conectividade:** validações falham rápido; o APK correto está no alvo correto e conversa com o servidor local.
- **M2 — Onboarding:** termos, preferências e seleção de uma entre quatro músicas observados no cliente e persistidos no perfil novo.
- **M3 — Tutorial:** multitouch sincronizado, playback e resultado real demonstrados; nenhum score/audit sintético.
- **M4 — E2E e documentação:** teste automatizado, evidências reproduzíveis e instruções para cada topologia.
- **M5 — Portabilidade:** repetir em emulador Docker e dispositivo físico, documentando diferenças e limitações.

Verificar primeiro com testes focados e depois com a suíte do servidor no `docker-dev`, sem montar o banco de desenvolvimento (`python -m pytest server/tests/ -v` no container descartável). Executar `python -m compileall -q server scripts` e `docker compose config --quiet`. O E2E real só pode ser marcado aprovado após executar contra o APK em ambos os alvos; testes unitários/HTTP não o substituem.

## Arquivos principais previstos

- `scripts/validate_emulator_song.py` — substituir ou descontinuar a semântica enganosa, mantendo compatibilidade deliberada se necessário.
- `scripts/android_song_autoplay.sh` — remover do caminho de aprovação E2E qualquer envio sintético de resultado.
- `scripts/patch_apk.py`, `client_patch/` — endpoint/identidade configuráveis e verificação do pacote.
- Novos scripts/módulos de pré-flight, checkpoints UI, multitouch e coleta de evidências.
- `server/handlers/songs_handler.py`, handlers de sessão/sync e `server/gameplay/` — suporte às respostas/eventos comprovados do onboarding.
- Testes em `server/tests/` e novos testes de automação/integração adequados ao ambiente Android.
- `docs/sot/music_asset_contract.md`, `docs/sot/client_patching_guide.md`, `docs/sot/protocol_specification.md`, `docs/README.md` — estado da evidência e operação.

## Frentes posteriores, separadas deste marco

1. Autenticação completa, validade/expiração de ticket e reuso de sessão observados no cliente.
2. Compras/economia em modo local, sem pagamentos externos.
3. Anúncios e callbacks/configuração em ambiente isolado, sem impressões reais.
4. Downloads, cache, compressão, formatos e aceitação nativa de assets.
5. Protocolo/gateway: framing, serialização, gzip e comandos reais observados.
6. Progressão além do tutorial, telemetria e outros comportamentos do cliente.
