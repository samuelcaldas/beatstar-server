# Scripts e pipeline de pesquisa

Os scripts são ferramentas de pesquisa/operação, não módulos do runtime. Cada
execução deve receber explicitamente seus arquivos de entrada e diretório de
saída; APKs, dumps, ferramentas e bancos locais são ignorados pelo Git.

## Taxonomia

- **Decompilação/análise:** `decompile.py`, `analyze_protocol.py`,
  `inspect_music_assets.py`, `extract_baked_assets.py`.
- **Assets/catalogação:** `import_unity_catalog.py`.
- **Patching do cliente:** `patch_apk.py`, `patch_ads_metadata.py` e os hooks
  em `client_patch/`.
- **Simulação sintética:** `simulate_autoplay.py`. Gera tráfego de protocolo e
  não prova que o APK reproduziu uma música.
- **Validação Android:** `validate_emulator_song.py`,
  `run_onboarding_e2e.py` e `android_song_autoplay.sh`. Só podem ser chamados
  E2E real quando registrarem APK, serial, endpoint, checkpoints observáveis e
  evidências; healthcheck ou audit sintético isolado não basta.

## Saídas

| Saída | Local |
| --- | --- |
| APKs e pacotes de distribuição | `dist/` |
| Extrações e dumps | `decompiled/` e `tools/` |
| Tentativas/intermediários | `tmp/` |
| Capturas Android/Playwright | `.playwright-mcp/` |
| Dados persistentes do servidor | `data/` |

Ao adicionar um script, inclua `--help`, valide argumentos antes de tocar em
arquivos e documente se o resultado é sintético, inspeção offline ou evidência
de execução no cliente real.
