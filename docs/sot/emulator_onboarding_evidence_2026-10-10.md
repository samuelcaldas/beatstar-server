# Evidências do onboarding e tutorial no emulador (2026-10-10)

Estado: **não concluído**. O tutorial foi iniciado com multitoque real, mas não houve prova de notas recebidas do servidor, nem de conclusão do tutorial, nem de E2E com asserções.

## Ambiente

- Emulador `emulator-5554`: `qemu-system-x86_64-headless @medium_phone -no-window` (sem janela; visualização por captura de tela).
- Imagem de produção: `adb root` negado; `/dev/input/event*` não gravável pelo shell.
- Servidor local: container `beatstar-private-server` (worktree `feature-patched-apk`), porta HTTP 8080 e gateway TCP 9099. Host `192.168.1.68`, alcançável pelo emulador.
- APK instalado (`com.spaceapegames.beatstar` 36.1.4.9545): `base.apk` sha256 `fc533048…`, `split_config.arm64_v8a.apk` sha256 `98eed882…`. Não corresponde aos `dist/*-patched.apk` do worktree (`b34c76d4…`, `a4ebbd54…`). Tem `res/xml/network_security_config.xml`, portanto é um build patched de outra origem. A configuração efetiva de endpoint não foi verificada.

## Fluxo observado (capturas em `.playwright-mcp/run_20261010_144352/`)

| Etapa | Captura | Observação |
|---|---|---|
| Tela inicial | 01 | "Tell us what music you're into!", botão LET'S GO |
| Gêneros | 02, 03 | "Tap once for like / twice for LOVE!"; Rock selecionado |
| Ano de nascimento | 04, 05 | "I was born in the…"; 90s selecionado |
| Descrição | 06 | "How do you describe yourself?"; "prefer not to say" escolhido |
| Seleção de tutorial | 07 | "SELECT YOUR TUTORIAL SONG": Unholy (Sam Smith, Kim Petras), Sweet Home Alabama (Lynyrd Skynyrd), Gangnam Style (Psy), Love The Way You Lie (Eminem) |
| Preview/PLAY | 08 | Unholy selecionada; PLAY |
| Tutorial | 08, 09 | "TAP TO START / Use Both Thumbs" |
| Início com 2 dedos | 14 | Pista ativa, feedback "PERFECT" após toque duplo injetado |

Os quatro starters acima foram lidos da tela. O servidor ainda devolve, em `songs_handler.py`, duas faixas fictícias (`starter_song_01/02`), e `onboarding_handler.py` contém IDs 710–713 inventados. Nenhum dos dois corresponde à tela. Ambos precisam ser substituídos com base no tráfego real.

## Tráfego do cliente (servidor)

- Gateway TCP 9099; 1 conexão persistente de `192.168.1.68`.
- Serviços observados: `ping` (94), `analyticsproxyservicev2` (38), `gameservice` (10), `notificationservice` (4), `cmsservice` (2), `userservice` (1).
- `gameservice` com `rpc_types` 5 e 28, respostas de 75–172 bytes. Os tipos não estão mapeados em `docs/sot/protocol_commands.json`, que não tem códigos numéricos.
- Nenhuma requisição HTTP a `/assets` ou a bundles.
- `songservice`/`beatmapservice` nunca foram chamados pelo cliente.
- CMS: `15 resources; real_bins=0 client_unchanged=15`, ou seja, o catálogo entrega placeholders.

**Conclusão:** não há evidência de que o servidor tenha enviado sequências de notas. A tela de tutorial abriu com dados que parecem vir do próprio APK. Para provar o contrário, é preciso capturar o corpo das respostas `gameservice` e verificar se algum payload contém dados de chart.

## Multitoque

- `input swipe` em paralelo: não iniciou o tutorial.
- `sendevent` em `/dev/input/event2`: `Permission denied`.
- `event send` no console do emulador: o overlay `pointer_location` mostrou `P: 0 / 0`, e `getevent` não registrou eventos. Não chega ao display.
- **Funcionou:** `scripts/android_multitouch/TwoThumbs.java` injeta `MotionEvent` multiponto via `IInputManager.injectInputEvent` (reflexão, sem `android.jar`). Dex gerado com `r8` 9.6.0-alpha02 (`~/.cache/beatstar-tools/r8.jar`). Executado com `app_process`, pressionou e manteve dois dedos (L 216,1680 / R 864,1680) por 2,5 s. A tela reagiu com "PERFECT".
- Limite: cada execução leva o tempo de inicialização do `app_process`. Não serve ainda para temporização de notas.

## Pendências para concluir a meta

1. Provar a entrega de notas: capturar corpos de `gameservice` e checar payloads.
2. Verificar a capa: aparece apagada pelo brilho do feedback; confirmar em quadro sem overlay.
3. Concluir o tutorial com temporização de notas (injetor persistente).
4. Substituir `STARTER_SONGS` por IDs e títulos reais do tráfego.
5. Ligar `--server-url` ao APK de fato (hoje é no-op) e verificar o endpoint efetivo no APK.
6. Transformar `scripts/run_onboarding_e2e.py` em E2E com asserções reais; o script atual só instala e tira uma captura.
