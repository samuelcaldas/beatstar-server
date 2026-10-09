/**
 * Beatstar Private Server - Frida Ads Hook Script
 * Controla Feature Flag de anúncios (VideoAdsEnabled), Ad Unit IDs e
 * auto-recompensa instantânea quando anúncios estão desabilitados.
 *
 * Referências SOT:
 * - FeatureFlags.get_VideoAdsEnabled (Assembly-CSharp)
 * - BaseVideoAdTracking.get_AdUnitId (Assembly-CSharp)
 * - BeatstarVideoAdController (Assembly-CSharp)
 */

const CONFIG_ENABLE_ADS = false; // Alterne para true para habilitar anúncios
const CUSTOM_REWARDED_UNIT = "6adcd39d323d305a";
const CUSTOM_INTERSTITIAL_UNIT = "075af25fa8b87ff7";

console.log("[*] Carregando módulo de controle de Anúncios Beatstar...");

Il2Cpp.perform(() => {
    try {
        const appAssembly = Il2Cpp.domain.assembly("Assembly-CSharp").image;

        // 1. Hook FeatureFlags.get_VideoAdsEnabled
        try {
            const featureFlags = appAssembly.class("FeatureFlags");
            featureFlags.method("get_VideoAdsEnabled").implementation = function () {
                console.log(`[Ads] FeatureFlags.get_VideoAdsEnabled -> ${CONFIG_ENABLE_ADS}`);
                return CONFIG_ENABLE_ADS;
            };
            console.log("[✓] Hook em FeatureFlags.get_VideoAdsEnabled aplicado!");
        } catch (err) {
            console.log("[-] Falha ao hookar FeatureFlags.get_VideoAdsEnabled:", err);
        }

        // 2. Custom Ad Units quando anúncios estão ativos
        if (CONFIG_ENABLE_ADS) {
            try {
                const baseTracking = appAssembly.class("BaseVideoAdTracking");
                baseTracking.method("get_AdUnitId").implementation = function () {
                    const original = this.method("get_AdUnitId").invoke();
                    console.log(`[Ads] BaseVideoAdTracking.get_AdUnitId (orig: ${original}) -> custom`);
                    return Il2Cpp.string(CUSTOM_REWARDED_UNIT);
                };
                console.log("[✓] Hook em BaseVideoAdTracking.get_AdUnitId aplicado!");
            } catch (err) {
                console.log("[-] Falha ao hookar BaseVideoAdTracking.get_AdUnitId:", err);
            }
        }

        console.log(`[✓] Módulo de Anúncios configurado (Enabled: ${CONFIG_ENABLE_ADS})`);
    } catch (e) {
        console.error("[-] Erro geral no hook de anúncios:", e);
    }
});
