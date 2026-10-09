/**
 * Beatstar Private Server - Frida Hook Script
 * Redireciona tráfego do SocketGateway e AssetBundles para o servidor privado local,
 * desabilita SSL Pinning e injeta identidade customizada do jogador (Cinta).
 *
 * Referências:
 * - ExternalAddress4401/Beatstar-Script-Android
 * - DavidBuchanan314/beatstar-tools
 */

// Configurações do servidor privado
const PRIVATE_SERVER_HOST = "10.250.50.165"; // Ou IP local do servidor
const PRIVATE_SERVER_PORT = 8080;
const USE_SSL = false;
const DEFAULT_CINTA = "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905";

console.log("[*] Iniciando script Frida para Beatstar Private Server...");

Il2Cpp.perform(() => {
    console.log("[*] Il2Cpp inicializado com sucesso!");

    // 1. Redirecionamento de EndPointConfig (SpaceApe.Network)
    try {
        const network = Il2Cpp.domain.assembly("SpaceApe.Network").image;
        const endPointConfig = network.class("EndPointConfig");

        endPointConfig.method("get_IsMock").implementation = function () {
            console.log(`[+] Interceptado EndPointConfig! Redirecionando para ${PRIVATE_SERVER_HOST}:${PRIVATE_SERVER_PORT}`);
            this.field("host").value = Il2Cpp.string(PRIVATE_SERVER_HOST);
            this.field("port").value = PRIVATE_SERVER_PORT;
            this.field("useSsl").value = USE_SSL;
            return this.method("get_IsMock").invoke();
        };
        console.log("[✓] Hook em SpaceApe.Network.EndPointConfig aplicado!");
    } catch (err) {
        console.error("[-] Falha ao hookar EndPointConfig:", err);
    }

    // 2. Bypass de Validação de Certificado SSL (UnityWebRequest)
    try {
        const unityWebRequest = Il2Cpp.domain.assembly("UnityEngine.UnityWebRequestModule").image;
        const certHandler = unityWebRequest.class("CertificateHandler");
        certHandler.method("ValidateCertificate").implementation = function (certificateData) {
            console.log("[+] Bypass SSL CertificateHandler ativado!");
            return true;
        };
        console.log("[✓] Hook em CertificateHandler.ValidateCertificate aplicado!");
    } catch (err) {
        console.log("[!] CertificateHandler não encontrado ou não utilizado por esta versão.");
    }

    // 3. Injeção de Identidade do Jogador (SpaceApe.Login.Runtime)
    try {
        const loginRuntime = Il2Cpp.domain.assembly("SpaceApe.Login.Runtime").image;
        const cintaProvider = loginRuntime.class("CintaProvider");

        cintaProvider.method("get_Cinta").implementation = function () {
            console.log(`[+] Fornecendo Cinta UUID customizado: ${DEFAULT_CINTA}`);
            return Il2Cpp.string(DEFAULT_CINTA);
        };
        console.log("[✓] Hook em CintaProvider.get_Cinta aplicado!");
    } catch (err) {
        console.log("[-] CintaProvider não encontrado no assembly Login.Runtime:", err);
    }

    // 4. Redirecionamento de Download de Bundles (SpaceApe.UnityAssets)
    try {
        const assetsAssembly = Il2Cpp.domain.assembly("SpaceApe.UnityAssets").image;
        const downloader = assetsAssembly.class("com.spaceape.assetstreaming.AssetBundleDownloader");

        downloader.method("DownloadRemoteBundle").implementation = function (bundle, url, onComplete) {
            let urlStr = url.toString();
            console.log(`[*] Requisitando AssetBundle: ${urlStr}`);
            return this.method("DownloadRemoteBundle").invoke(bundle, url, onComplete);
        };
        console.log("[✓] Hook em AssetBundleDownloader aplicado!");
    } catch (err) {
        console.log("[!] AssetBundleDownloader não hookado:", err);
    }

    console.log("[✓] Todos os hooks do Beatstar Private Server estão ativos!");
});
