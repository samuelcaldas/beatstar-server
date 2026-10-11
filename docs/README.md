# Beatstar Private Server & Reverse Engineering - Documentação

Este diretório contém a documentação técnica, especificações de protocolo (Source of Truth), registros de decisões arquiteturais (ADR) e referências de engenharia reversa do jogo **Beatstar** (Space Ape Games).

- [Mapa arquitetural](architecture.md) - responsabilidades, dependências,
  contratos e política de artefatos do repositório.

---

## Estrutura da Documentação

### 1. Referências Externas (`docs/references/`)
- [01_beatstar_script_android.md](references/01_beatstar_script_android.md) - Análise do repositório `ExternalAddress4401/Beatstar-Script-Android`: hooking via Frida, `EndPointConfig`, `CintaProvider` e injeção de assets.
- [02_beatstar_tools.md](references/02_beatstar_tools.md) - Análise do repositório `DavidBuchanan314/beatstar-tools`: enquadramento binário de pacotes do `SocketGateway`, parser Protobuf/Raksha, `userservice` e `cmsservice`.

### 2. Fontes de Verdade (`docs/sot/`)
- [music_asset_contract.md](sot/music_asset_contract.md) - Registro de evidências dos assets musicais: presença, extração offline e decodificação de charts são observadas; vínculos e semântica nativa não são comprovados; exportação e reprodução Android estão BLOQUEADAS.
- [protocol_specification.md](sot/protocol_specification.md) - Especificação completa do protocolo SpaceApe Sharpla e SocketGateway.
- [decompilation_guide.md](sot/decompilation_guide.md) - Manual de extração de assets, IL2CPP dump e descompilação C#/Java.
- [client_patching_guide.md](sot/client_patching_guide.md) - Instruções para patch de APK e injeção de hooks para conexão do cliente ao servidor privado.
- [ads_and_monetization_guide.md](sot/ads_and_monetization_guide.md) - Guia de configuração de Feature Flag e injeção de conta personalizada do Google Ads / AdMob & AppLovin.
- [commerce_and_feature_flags_guide.md](sot/commerce_and_feature_flags_guide.md) - Guia de Feature Flags de compras e SDK de comércio server-side (IAP, Loja, Lootboxes, Tour Pass, Skins).
- [gameplay_and_progression_guide.md](sot/gameplay_and_progression_guide.md) - Guia de arquitetura e SDK do sistema de progressão de níveis (Venues/Jornada), multi-usuários, ranking (Leaderboards) e brags/desafios.


### 3. Decisões Arquiteturais (`docs/adr/`)
- [0001-decompilation-and-server-architecture.md](adr/0001-decompilation-and-server-architecture.md) - Decisão arquitetural de ferramentas de descompilação e stack do servidor privado em Python (FastAPI).

### Planos e operação

- [Planos históricos](plans/README.md)
- [Pipeline de scripts](../scripts/README.md)
