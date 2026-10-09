# Guia de Conexão do Cliente ao Servidor Privado

Para que o aplicativo Android Beatstar conecte ao nosso emulador de servidor privado em vez dos servidores desligados da Space Ape, existem duas abordagens complementares:

---

## 1. Método A: APK Modificado e Assinado (Recomendado)

O script `scripts/patch_apk.py` desempacota o APK, injeta uma política de segurança de rede permissiva (`client_patch/network_security_config.xml`), habilita tráfego em cleartext HTTP e assina com um debug keystore.

### Passos:
```bash
# 1. Gerar o APK patcheado a partir do base.apk extraído
python3 scripts/patch_apk.py --apk decompiled/extracted/base.apk --output-apk dist/beatstar-patched.apk

# 2. Instalar no dispositivo / emulador via ADB
adb install dist/beatstar-patched.apk
```

---

## 2. Método B: Injeção Dinâmica via Frida (Sem Modificar o APK)

Utiliza o script `client_patch/frida_hook_network.js` para interceptar em tempo de execução:
- `SpaceApe.Network.EndPointConfig.get_IsMock`: Redireciona IP e porta do `SocketGateway`.
- `UnityEngine.Networking.CertificateHandler.ValidateCertificate`: Desabilita SSL Pinning.
- `SpaceApe.Login.Runtime.CintaProvider.get_Cinta`: Fornece a identidade do usuário.

### Passos:
1. Inicie o servidor do Frida no Android (`frida-server`).
2. Execute o hook:
   ```bash
   frida -U -f com.spaceapegames.beatstar -l client_patch/frida_hook_network.js
   ```

---

## 3. Configuração de DNS / Proxy (Nginx Proxy Manager/Traefik)

Caso prefira redirecionar através de DNS local (instancia docker local):
- Aponte o domínio `socket-gateway.prod.flamingo.apelabs.net` para o IP do servidor emulador (`10.250.50.165`).
- No Traefik, configure o Proxy Host encaminhando a porta `8080`.
