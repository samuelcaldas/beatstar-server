# Guia de Configuração e Feature Flag do Sistema de Anúncios (Google Ads / AdMob & AppLovin MAX)

Este guia documenta o Source of Truth (SOT) da arquitetura de monetização do Beatstar e fornece instruções para alternar a **Feature Flag** de anúncios e injetar sua **conta de anúncios própria**.

---

## 1. Arquitetura de Anúncios no Beatstar

A versão Android do Beatstar utiliza uma camada híbrida de monetização:
1. **Google Mobile Ads SDK (AdMob)**:
   - Registrado no `AndroidManifest.xml` via tag `<meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" .../>`.
   - Inicializa a pilha de mediação do Google Play Services.
2. **AppLovin MAX / Unity IL2CPP**:
   - `AppConfig.APPLOVIN_REWARDED_AD_UNIT_ID_ANDROID` (String literal padrão: `6adcd39d323d305a`).
   - `AppConfig.APPLOVIN_INTERSTITIAL_AD_UNIT_ID_ANDROID` (String literal padrão: `075af25fa8b87ff7`).
   - `FeatureFlags.get_VideoAdsEnabled` (RVA `0x28F57C4`): consulta o campo `_VideoAdsEnabled` proveniente do catálogo CMS `GameConfig`.
   - `BeatstarVideoAdController`: gerencia exibição, recompensas e callbacks.

---

## 2. Configuração no Servidor Privado

O servidor expõe variáveis de ambiente no arquivo `.env` para ligar/desligar o sistema de anúncios e customizar os identificadores de monetização.

### Variáveis no `.env`:
```bash
# Habilita ou desabilita anúncios globalmente (true/false)
FEATURE_FLAG_GOOGLE_ADS_ENABLED=false

# Google Ads / AdMob App ID
GOOGLE_ADS_APP_ID=ca-app-pub-9249007709450981~3951571657

# Unidades de Anúncio Customizadas
GOOGLE_ADS_REWARDED_UNIT_ID=6adcd39d323d305a
GOOGLE_ADS_INTERSTITIAL_UNIT_ID=075af25fa8b87ff7
```

### Comportamento no Servidor:
- O endpoint `/assets/configs/GameConfig` injeta `"VideoAdsEnabled": true/false` no objeto `FeatureFlagsConfig`.
- O endpoint `/assets/configs/AdsConfig` entrega as configurações de rede, placements e Ad Unit IDs correspondentes às variáveis do `.env`.

---

## 3. Patching do APK (Injeção de Conta Customizada)

Para que o APK utilize sua conta do Google Ads / AdMob ao invés do App ID original da Space Ape, utilize o script `scripts/patch_apk.py`:

```bash
# Desabilitar anúncios no APK
python3 scripts/patch_apk.py \
  --apk storage/apks/base.apk \
  --output-apk dist/beatstar-patched.apk \
  --disable-ads

# Habilitar anúncios com sua conta customizada
python3 scripts/patch_apk.py \
  --apk storage/apks/base.apk \
  --output-apk dist/beatstar-patched.apk \
  --ads-app-id "ca-app-pub-1234567890123456~1234567890" \
  --rewarded-ad-unit "custom_reward_id" \
  --interstitial-ad-unit "custom_inter_id" \
  --enable-ads
```

---

## 4. Patching Binário de Ad Units (`global-metadata.dat`)

Para substituir as strings de Ad Unit em tempo de build ou em arquivos extraídos sem recompilar o jogo:

```bash
python3 scripts/patch_ads_metadata.py \
  --metadata storage/decompiled/apk_extracted/assets/bin/Data/Managed/Metadata/global-metadata.dat \
  --rewarded-id "custom_reward_id" \
  --interstitial-id "custom_inter_id"
```

---

## 5. Controle em Tempo de Execução via Frida

Para testar ou alternar a flag sem reconstruir o APK, utilize o script `client_patch/frida_hook_ads.js`:

```bash
frida -U -f com.spaceapegames.beatstar -l client_patch/frida_hook_ads.js
```

No topo do arquivo `client_patch/frida_hook_ads.js`, altere:
```javascript
const CONFIG_ENABLE_ADS = true; // ou false
const CUSTOM_REWARDED_UNIT = "seu_ad_unit_id";
```
