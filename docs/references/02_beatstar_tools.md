# Referência Externa 2: beatstar-tools

- **Repositório**: [DavidBuchanan314/beatstar-tools](https://github.com/DavidBuchanan314/beatstar-tools)
- **Branch de Referência**: `main`
- **Foco Principal**: Engenharia reversa de rede, protocolo binário do gateway de sockets, parser de Raksha/Protobuf e ferramentas de extração de dados.

---

## 1. Arquitetura de Rede Space Ape Revelada

### 1.1 Endpoint Padrão Oficial
- Hostname: `socket-gateway.prod.flamingo.apelabs.net`
- Porta: `443` (com SSL/TLS)

### 1.2 Estrutura de Enquadramento de Pacotes (Wire Format)
A comunicação com o `SocketGateway` segue um protocolo binário estruturado com cabeçalhos de comprimento e serialização Protobuf/Raksha:

```
+---------------------------+----------------------------+-----------------------+----------------------+
| 4 bytes (Big-Endian uint) | 4 bytes (Big-Endian uint)  | N bytes (Protobuf)    | M bytes (Protobuf)   |
| Comprimento Total Pacote  | Comprimento do Cabeçalho   | Request/Response Hdr  | Request/Response Body|
+---------------------------+----------------------------+-----------------------+----------------------+
```

1. **`pktlen`** (uint32 big-endian): Tamanho total de `header_len + header_bytes + body_bytes`.
2. **`header_len`** (uint32 big-endian): Tamanho do payload do cabeçalho em bytes.
3. **`header_bytes`**: Objeto Protobuf contendo metadados de roteamento (ex: `service`, `version`, `rpcthing`, `authenticationTicket`, `clide`).
4. **`body_bytes`**: Objeto Protobuf do comando específico. Se o cabeçalho indicar `gzipped: 1`, os bytes do corpo vêm compactados com Gzip.

### 1.3 Serviços Fundamentais

#### A. `userservice` (Autenticação e Sessão)
- **`BaseReq`**:
  - `type: 7` (`AllInOneLogin`) ou `type: 2` (`Login`).
  - Campo `all_in_one_login`: Contém o identificador `cinta` (UUID do jogador).
- **`BaseResp`**:
  - Retorna `status: 200`, `authenticationTicket`, `clide` e `cinta`.
  - Este `authenticationTicket` é reutilizado em todas as requisições subsequentes.

#### B. `cmsservice` (Configurações do Jogo e Catálogo de Músicas)
- Requisita e sincroniza os catálogos centrais:
  - `GameConfig`: Tabela mestre de atributos de gameplay, regras e caixas.
  - `LangConfig`: Localização e strings (en, pt-BR, etc.).
  - `AssetsPatchConfig`: URLs e hashes dos AssetBundles atualizados.
  - `AudioConfig`: Metadados das faixas de áudio e transições.
  - `MusicKitConfig`: Integração de metadados das faixas.

### 1.4 Parser Raksha / Protobuf (`raksha.py`)
O formato de serialização da Space Ape é uma implementação compacta de Protobuf variante (denominada internamente Raksha), suportando tipos como:
- `Varint`: Inteiros codificados em base-128.
- `String`: Strings codificadas em UTF-8 com prefixo de tamanho.
- `Bytes`: Arrays binários.
- `Packed`: Vetores compactados de tipos primitivos.

---

## 2. Aplicação no Nosso Projeto
1. **Modelagem do Servidor Gateway**: A implementação em `server/gateway/` espelha o enquadramento de 4 bytes + 4 bytes com suporte a Gzip e despacho para `userservice`, `cmsservice` e comandos de gameplay `Flamingo`.
2. **Banco de Dados de Configurações**: Utilizaremos os esquemas de `GameConfig` e `AudioConfig` para popular os modelos de músicas do servidor privado.
3. **Autenticação**: O servidor fornecerá respostas compatíveis para `all_in_one_login` persistindo a chave `cinta`.
