/**
 * Beatstar Private Server - Frida Commerce & Feature Flags Hook Script
 * Controla em tempo de execução todas as Feature Flags de compras no APK:
 * - IAP & Gemas
 * - Loja & Bundles
 * - Lootboxes & Song Cases
 * - Modo Premium & Tour Pass
 * - Capas, Cosméticos e Skins de Trilha
 *
 * Referências SOT:
 * - FeatureFlags (Assembly-CSharp)
 * - SpaceApe.Payments (SpaceApe.Payments.dll)
 */

// Configurações das Feature Flags de Compras (true = habilitado, false = desabilitado)
const CONFIG_IAP_ENABLED = false;            // Compras com dinheiro real / pacotes de gemas
const CONFIG_SHOP_ENABLED = true;            // Loja de itens e pacotes
const CONFIG_LOOTBOXES_ENABLED = true;       // Abertura de caixas / song cases e gacha
const CONFIG_PREMIUM_PASS_ENABLED = true;    // Modo Premium / Temporadas do Tour Pass
const CONFIG_COSMETICS_ENABLED = true;       // Capas, banners e skins de trilha

console.log("[*] Carregando módulo Frida de Commerce & Feature Flags...");

Il2Cpp.perform(() => {
    try {
        const appAssembly = Il2Cpp.domain.assembly("Assembly-CSharp").image;
        const featureFlags = appAssembly.class("FeatureFlags");

        const hooks = [
            { method: "get_SeasonsEnabled", value: CONFIG_PREMIUM_PASS_ENABLED, name: "Premium Pass" },
            { method: "get_TourPassBoostersEnabled", value: CONFIG_PREMIUM_PASS_ENABLED, name: "Tour Pass Boosters" },
            { method: "get_ThemedBoxesEnabled", value: CONFIG_LOOTBOXES_ENABLED, name: "Lootboxes / Cases" },
            { method: "get_TrackSkinsEnabled", value: CONFIG_COSMETICS_ENABLED, name: "Track Skins / Capas" },
            { method: "get_LiveOpsBundlesEnabled", value: CONFIG_SHOP_ENABLED, name: "Shop Bundles" },
            { method: "get_LeaderboardEventsShop", value: CONFIG_SHOP_ENABLED, name: "Leaderboard Shop" },
            { method: "get_CanPurchaseMoreGemsFromContinue", value: CONFIG_IAP_ENABLED, name: "IAP from Continue" },
            { method: "get_CanPurchaseMoreGemsFromBundlesPopup", value: CONFIG_SHOP_ENABLED, name: "Gems from Bundles" },
            { method: "get_NotEnoughGemsShowIAPPopup", value: CONFIG_IAP_ENABLED, name: "Not Enough Gems IAP" },
        ];

        for (const item of hooks) {
            try {
                featureFlags.method(item.method).implementation = function () {
                    return item.value;
                };
                console.log(`[✓] Feature Flag hookada: ${item.name} (${item.method} -> ${item.value})`);
            } catch (err) {
                // Método não encontrado nesta versão específica
            }
        }

        console.log("[✓] Módulo Frida de Commerce & Feature Flags carregado com sucesso!");
    } catch (e) {
        console.error("[-] Erro ao inicializar hooks de Commerce:", e);
    }
});
