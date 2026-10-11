# Descobertas sobre o APK original

Registro de comportamento observado no cliente original (`36.1.4.9545`). Cada item indica a
fonte. Itens sem evidência de código ficam marcados como pendentes.

Artefatos gerados (git-ignored):
- `decompiled/il2cpp/dump.cs`, `script.json`, `DummyDll/`: IL2CPP do `libil2cpp.so` arm64-v8a.
- `decompiled/csharp/`: 10 assemblies-chave descompilados com ilspycmd (4005 arquivos `.cs`).
- `decompiled/java/`: DEX do `base.apk` descompilado com JADX (25345 arquivos `.java`).

## Limitação dos dumps

- Os corpos dos métodos nas DLLs dummy estão vazios. O C# mostra assinaturas, campos e
  atributos (`[Token]`, `[Address]`), não a lógica. O comportamento precisa de Java,
  strings, tráfego capturado ou análise do binário nativo.

## Autenticação

- `BaseReq` (`SpaceApe.Login.Runtime`) carrega `authenticationTicket` como campo de
  string, junto com `id`, `type`, `appVersion` e `timestamp`. Fonte: C#.
- `RespAllInOneLogin` e `RespRefreshTicket` também recebem `authenticationTicket`.
  Existe um fluxo de renovação (`ReqRefreshTicket`, `RefreshTicketCommand`,
  `RefreshAuth`). Fonte: C#.
- `Authentication` (`SpaceApe.Rpc`) implementa `RefreshAuth`. Não foi possível confirmar
  pelo C# em que momento o cliente renova o ticket, porque o corpo está vazio.
- Pendente: confirmar pelo tráfego real que o cliente reenvia o ticket nas requisições
  seguintes (requisito da decisão 4 antes de ativar a enforcement).

## Endpoints

- URLs encontradas no código: `https://www.nextbeat.com/bs/oauth/scid`,
  `https://assets.flamingo.newbirds.net/flamingo-asset-bundles/prod`,
  `https://accounts.supercell.com/oauth/authorize`, suporte Zendesk. Fonte: C# e Java.
- Pendente: o endpoint de gateway usado pelo cliente não aparece como URL literal. Vem
  da configuração de `RpcServicesConfig`, que precisa de análise dos assets.

## Pendências de investigação

- Como o cliente monta o cabeçalho e o corpo do gateway (JSON ou protobuf).
- Quais serviços existem além de `userservice`, `cmsservice`, `profileservice`,
  `syncservice`, `songservice` e `beatmapservice` (já usados pelo servidor).
