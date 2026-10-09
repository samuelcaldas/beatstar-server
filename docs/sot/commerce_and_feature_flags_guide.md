# Guia de Feature Flags de Compras e SDK de Comércio Server-Side

Este documento serve como Fonte da Verdade (SOT) para os subsistemas de compras e economia do Beatstar, detalhando o mapeamento de **Feature Flags** e o funcionamento do **SDK de Comércio Server-Side** implementado no servidor privado.

---

## 1. Mapeamento de Feature Flags de Compras

Todos os elementos de compra do jogo foram convertidos em Feature Flags controláveis no servidor via `.env`, na entrega do CMS `GameConfig`, em tempo de execução com Frida, e no patcher de APK.

| Domínio de Compra | Flag no `.env` | Chave em `FeatureFlagsConfig` | Impacto no Cliente Beatstar |
| :--- | :--- | :--- | :--- |
| **IAP & Gemas** | `FEATURE_FLAG_IAP_ENABLED=false` | `CanPurchaseMoreGemsFromContinue`, `NotEnoughGemsShowIAPPopup` | Ativa/desativa popups de compra de gemas com dinheiro real. |
| **Loja & Bundles** | `FEATURE_FLAG_SHOP_ENABLED=true` | `LiveOpsBundlesEnabled`, `LeaderboardEventsShop`, `ShopBundlesUseStreamingAssets` | Habilita a aba de loja geral, promoções diárias e pacotes de moedas. |
| **Lootboxes / Caixas**| `FEATURE_FLAG_LOOTBOXES_ENABLED=true` | `ThemedBoxesEnabled`, `LeaderboardEventGachaPurchaseFlowEnabled` | Habilita compra e abertura de Caixas de Gênero (Rock, Pop, etc.) e aceleração de abertura. |
| **Modo Premium / Tour Pass**| `FEATURE_FLAG_PREMIUM_PASS_ENABLED=true` | `SeasonsEnabled`, `TourPassBoostersEnabled`, `DeluxeModeEnabled` | Ativa a trilha de temporadas, compra de tiers e passe premium. |
| **Capas & Cosméticos**| `FEATURE_FLAG_COSMETICS_ENABLED=true` | `TrackSkinsEnabled`, `CosmeticsRefreshHashCodeEnabled` | Habilita skins de pista, banners de perfil e efeitos visuais. |

---

## 2. Arquitetura do Commerce SDK Server-Side (`server/commerce/`)

O SDK server-side foi projetado com isolamento de responsabilidade, princípios SOLID e validação Fail-Fast:

- **`CommerceFeatureFlagManager`**: Valida se uma operação é permitida com base nas flags ativas. Se a flag estiver desligada, lança `CommerceFeatureDisabledError`.
- **`StoreCatalog`**: Mantém o repositório em memória de produtos disponíveis (pacotes de moedas, caixas temáticas, skins e tour pass).
- **`WalletManager`**: Valida fundos estritamente antes de qualquer transação (`InsufficientFundsError`), debitando moedas/gemas e creditando recompensas.
- **`GachaLootboxEngine`**: Resolve o algoritmo de premiação ao abrir caixas de músicas (desbloqueio de faixas novas, cartas ou moedas).
- **`TourPassManager`**: Gerencia temporadas, avanço de níveis e desbloqueio da trilha premium.
- **`CommerceService`**: Fachada orquestradora que coordena a transação de ponta a ponta e garante a persistência no SQLite.

---

## 3. Endpoints REST da API de Comércio (`/api/commerce/`)

O servidor expõe endpoints HTTP para gerenciamento e testes:

### Consultar Feature Flags
```bash
GET /api/commerce/flags
```
**Resposta:**
```json
{
  "iap_enabled": false,
  "shop_enabled": true,
  "lootboxes_enabled": true,
  "premium_pass_enabled": true,
  "cosmetics_enabled": true
}
```

### Alterar Feature Flag em Runtime
```bash
POST /api/commerce/flags
Content-Type: application/json

{"flag_name": "iap_enabled", "enabled": true}
```

### Consultar Catálogo de Produtos
```bash
GET /api/commerce/catalog
```

### Consultar Carteira e Inventário do Jogador
```bash
GET /api/commerce/wallet/{cinta}
```

### Conceder Moedas ou Gemas (Teste / Admin)
```bash
POST /api/commerce/grant
Content-Type: application/json

{"cinta": "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905", "currency": "gems", "amount": 500}
```

---

## 4. Integração com Auditorias do Jogo (`SyncHandler`)

O `SyncHandler` intercepta auditorias enviadas pelo APK durante o jogo e as encaminha ao `CommerceService`:
- `BuyShopItem_SharplaAudit`: Compra de itens da loja por gemas/moedas.
- `BuyShopThemedBox_SharplaAudit`: Compra de caixas temáticas.
- `StartIAPPurchase_SharplaAudit` / `CompleteIAPPurchase_SharplaAudit`: Compras de gemas.
- `OpenCampaignGachaBox_SharplaAudit`: Desbloqueio e abertura de caixas de cartas.
- `Season_BuyLevel_SharplaAudit`: Avanço de níveis no Tour Pass.
- `SetGlobalTrackSkin_SharplaAudit`: Equipe de capas/skins de trilha.

---

## 5. Controle no Cliente via Frida

O script `client_patch/frida_hook_commerce.js` permite forçar valores de feature flags em tempo de execução no cliente Unity IL2CPP:

```bash
frida -U -f com.spaceapegames.beatstar -l client_patch/frida_hook_commerce.js
```
