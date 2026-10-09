# Referência Externa 1: Beatstar-Script-Android

- **Repositório**: [ExternalAddress4401/Beatstar-Script-Android](https://github.com/ExternalAddress4401/Beatstar-Script-Android)
- **Branch de Referência**: `main`
- **Foco Principal**: Automação e injeção dinâmica via Frida (`frida-il2cpp-bridge`), hooking de servidor privado e injeção de assets locais.

---

## 1. Principais Mecanismos Identificados

### 1.1 Redirecionamento para Servidor Privado (`utilities/customServer.ts`)
O Beatstar utiliza a classe `EndPointConfig` no assembly `SpaceApe.Network`. O hook substitui dinamicamente os campos de conexão para apontar para o IP/porta do servidor local/privado:

```typescript
export const customServer = () => {
  const network = Il2Cpp.domain.assembly("SpaceApe.Network").image;

  network.class("EndPointConfig").method("get_IsMock").implementation =
    function () {
      const ip = SettingsReader.getSetting("serverIp");
      this.field("host").value = Il2Cpp.string(ip);
      this.field("port").value = SettingsReader.getSetting("serverPort");
      this.field("useSsl").value = false;
      return this.method("get_IsMock").invoke();
    };
};
```

### 1.2 Persistência e Identidade do Jogador (`private-server/hookCintaId.ts`)
A identidade do usuário Space Ape é baseada no identificador `cinta` (UUID v4) gerenciado por `SpaceApe.Login.Runtime.CintaProvider`:

```typescript
export const hookCintaId = () => {
  const loginRuntime = Il2Cpp.domain.assembly("SpaceApe.Login.Runtime").image;

  loginRuntime.class("CintaProvider").method("get_Cinta").implementation =
    function () {
      const cinta = Il2Cpp.string(
        fs.readFileSync("sdcard/beatstar/user").toString()
      );
      setCinta(cinta.content);
      return cinta;
    };
};
```

### 1.3 Interceptação de AssetBundles e Músicas Customizadas (`customs/hookRemoteBundles.ts`)
O download de bundles de áudio, charts e capas de álbum é interceptado em `SpaceApe.UnityAssets`:

```typescript
export const hookRemoteBundles = () => {
  const assembly = Il2Cpp.domain.assembly("SpaceApe.UnityAssets").image;

  assembly
    .class("com.spaceape.assetstreaming.AssetBundleDownloader")
    .method("DownloadRemoteBundle").implementation = function (
    bundle: any,
    url: Il2Cpp.String,
    onComplete: any
  ) {
    // Redireciona download de audio.bundle, artwork.bundle, chart.bundle
    return this.method("DownloadRemoteBundle").invoke(bundle, url, onComplete);
  };
};
```

### 1.4 Bypass de Validação de Checksum e Hash
- `hacks/disableChecksum.ts`: Desabilita a conferência de integridade local de arquivos de beatmaps.
- `customs/ignoreBundleHash.ts`: Ignora a verificação de hash MD5/SHA de AssetBundles remotos baixados pelo jogo.

---

## 2. Aplicação no Nosso Projeto
1. **Hook de Frida**: Disponibilizado em `client_patch/frida_hook_network.js` para testes imediatos sem alteração de binário.
2. **Patch de APK**: O comportamento de `EndPointConfig` (`host`, `port`, `useSsl = false`) e `CintaProvider` orienta onde modificar o código IL2CPP ou parâmetros no `dump.cs` / `libil2cpp.so`.
3. **Servidor de Assets**: O servidor privado em FastAPI incluirá rotas compatíveis com o formato esperado de bundle streaming (`/5/...`, `/emoji/...`, `/streamedimages/...`).
