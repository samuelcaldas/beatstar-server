# Guia do SDK de Gameplay, Progressão, Multi-usuários e Ranking

Este documento estabelece o Source of Truth (SOT) para as regras de negócio de gameplay, níveis de jornada, sistema de múltiplos usuários, placares e desafios do emulador do **Beatstar**.

---

## 1. Sistema de Nível e Progressão (Journey / Star Milestones)

A progressão do jogador é determinada pelo **número cumulativo de estrelas** obtidas ao tocar músicas, avançando por palcos de show chamados **Venues**:

### Escala de Venues e Desbloqueios:
| Nível | Nome do Venue | Estrelas Necessárias | Músicas Desbloqueadas | Bônus ao Atingir |
| :---: | :--- | :---: | :--- | :--- |
| **1** | The Garage | 0 ★ | `starter_song_01`, `starter_song_02` | - |
| **2** | The Pub | 5 ★ | `song_rock_01` | +100 🪙 / +10 💎 |
| **3** | The Club | 15 ★ | `song_pop_01` | +100 🪙 / +10 💎 |
| **4** | The Warehouse | 30 ★ | `song_electronic_01` | +100 🪙 / +10 💎 |
| **5** | The Arena | 50 ★ | `song_rock_02` | +100 🪙 / +10 💎 |
| **6** | The Amphitheatre | 75 ★ | `song_pop_02` | +100 🪙 / +10 💎 |
| **7** | The Festival | 110 ★ | `song_electronic_02` | +100 🪙 / +10 💎 |
| **8** | The Stadium | 150 ★ | `song_extreme_01` | +100 🪙 / +10 💎 |
| **9** | The Metropolis | 200 ★ | `song_extreme_02` | +100 🪙 / +10 💎 |
| **10**| The Hall of Fame | 260 ★ | `song_master_01` | +100 🪙 / +10 💎 |

---

## 2. Sistema de Pontuação e Medalhas

Cada partida avalia a pontuação com base nas batidas (*Taps*, *Holds*, *Swipes*, *Flicks*):

| Faixa de Pontuação | Estrelas Concedidas | Medalha Conquistada |
| :--- | :---: | :--- |
| **50.000 pts** | 5 ★ | **Diamond Perfect** (100% Perfect+) |
| **49.500 a 49.999 pts** | 5 ★ | **Diamond** |
| **49.000 a 49.499 pts** | 5 ★ | **Platinum** |
| **48.000 a 48.999 pts** | 5 ★ | **Gold** |
| **35.000 a 47.999 pts** | 4 ★ | Nenhuma |
| **20.000 a 34.999 pts** | 3 ★ | Nenhuma |
| **10.000 a 19.999 pts** | 2 ★ | Nenhuma |
| **2.500 a 9.999 pts** | 1 ★ | Nenhuma |

---

## 3. Sistema Multi-usuários e Amizades

- **Identidade**:
  - `Cinta UUID`: Chave primária permanente persistida no dispositivo do jogador.
  - `Clide`: Chave curta do cliente de 8 caracteres gerada para exibição em rankings e amizades.
- **Amizades (`AddFriend_Req` / `player_friends`)**:
  - Conexão bidirecional entre contas.
  - Permite filtrar rankings apenas entre amigos (`friendsOnly: true`).

---

## 4. Rankings e Placares (`LeaderboardWithViews_Req`)

O servidor calcula rankings em tempo real persistidos no SQLite:
1. **Ranking por Música**: Ordena todos os jogadores pela maior pontuação obtida na música.
2. **Ranking Global**: Soma cumulativa dos melhores recordes de cada jogador em todo o repertório.
3. **Filtro de Amigos**: Exibe a classificação comparando apenas os jogadores da lista de amigos.

---

## 5. Sistema de Desafios e Provocações (Brags)

Quando um jogador bate o recorde de um amigo em qualquer música:
1. O servidor emite automaticamente um registro `FriendBragRecord` em `player_brags`.
2. O amigo desafiado recebe a notificação do score a ser superado (`score_to_beat`).
3. Ao jogar novamente e igualar ou superar o score, o desafio é marcado como `beaten = true`.

---

## 6. Endpoints REST da API de Gameplay (`/api/gameplay/`)

- `GET /api/gameplay/progression/{cinta}`: Consulta venue, nível, estrelas e músicas liberadas.
- `GET /api/gameplay/leaderboards/global`: Consulta o ranking geral.
- `GET /api/gameplay/leaderboards/song/{song_id}`: Consulta o ranking de uma música específica.
- `POST /api/gameplay/scores/submit`: Submissão de desempenho com auditoria e verificação de nível.
- `GET /api/gameplay/friends/{cinta}`: Lista de amigos do jogador.
- `POST /api/gameplay/friends/add`: Adiciona amigo via cinta ou clide.
- `GET /api/gameplay/brags/{cinta}`: Consulta desafios recebidos pendentes.
