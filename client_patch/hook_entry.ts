import "frida-il2cpp-bridge";

const PRIVATE_SERVER_HOST = "10.0.2.2";
const PRIVATE_SERVER_PORT = 8080;
const USE_SSL = false;
const DEFAULT_CINTA = "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905";

console.log("[*] Beatstar hook loading...");

Il2Cpp.perform(() => {
    console.log("[*] Il2Cpp initialized!");

    // 1. Redirect EndPointConfig to private server
    try {
        const network = Il2Cpp.domain.assembly("SpaceApe.Network").image;
        const endPointConfig = network.class("EndPointConfig");

        endPointConfig.method("get_IsMock").implementation = function () {
            console.log(`[+] EndPointConfig -> ${PRIVATE_SERVER_HOST}:${PRIVATE_SERVER_PORT}`);
            (this as Il2Cpp.Object).field("host").value = Il2Cpp.string(PRIVATE_SERVER_HOST);
            (this as Il2Cpp.Object).field("port").value = PRIVATE_SERVER_PORT;
            (this as Il2Cpp.Object).field("useSsl").value = USE_SSL;
            return (this as Il2Cpp.Object).method("get_IsMock").invoke();
        };
        console.log("[✓] EndPointConfig hooked");
    } catch (err) {
        console.error("[-] EndPointConfig failed:", err);
    }

    // 2. SSL bypass
    try {
        const unityWebRequest = Il2Cpp.domain.assembly("UnityEngine.UnityWebRequestModule").image;
        const certHandler = unityWebRequest.class("CertificateHandler");
        certHandler.method("ValidateCertificate").implementation = function () {
            return true;
        };
        console.log("[✓] SSL bypass active");
    } catch (err) {
        console.log("[!] SSL bypass not needed or failed:", err);
    }

    // 3. Inject Cinta identity
    try {
        const loginRuntime = Il2Cpp.domain.assembly("SpaceApe.Login.Runtime").image;
        const cintaProvider = loginRuntime.class("CintaProvider");
        cintaProvider.method("get_Cinta").implementation = function () {
            return Il2Cpp.string(DEFAULT_CINTA);
        };
        console.log("[✓] CintaProvider hooked -> " + DEFAULT_CINTA);
    } catch (err) {
        console.log("[-] CintaProvider failed:", err);
    }

    console.log("[✓] All hooks active!");
});
