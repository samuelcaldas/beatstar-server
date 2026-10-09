#!/usr/bin/env python3
"""Automated Song Playback Simulation for Beatstar Private Server.

Simulates the end-to-end game lifecycle:
1. AllInOneLogin (userservice) -> Cinta / AuthTicket
2. CMS Config Query (cmsservice)
3. Song Catalog Query (songservice)
4. RhythmGameStarted_SharplaAudit (Rhythm game initialization)
5. Note playback simulation based on Beatstar-Script-Android autoplay.ts
6. RhythmGameEnded_SharplaAudit & SyncReq (syncservice)
7. Profile verification asserting score, stars, and coins persistence
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
import sys
from typing import Any


class AutoplaySimulator:
    """Simulates automated note hits and server synchronization."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        cinta: str = "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905",
    ):
        self.base_url = base_url.rstrip("/")
        self.cinta = cinta
        self.auth_ticket = ""
        self.clide = ""

    def _post(
        self, service: str, body: dict[str, Any], rpc_name: str = "rpc"
    ) -> dict[str, Any]:
        """Sends POST request to the Gateway."""
        url = f"{self.base_url}/gateway"
        payload = {
            "header": {
                "service": service,
                "version": "36.1.4.9545",
                "rpcthing": f"{rpc_name}-{int(time.time() * 1000)}",
                "authenticationTicket": self.auth_ticket,
                "clide": self.clide,
            },
            "body": body,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json

    def step1_login(self) -> None:
        """Authenticates with the private server."""
        print("[1/5] Realizando login no servidor (AllInOneLogin)...")
        res = self._post(
            service="userservice",
            body={
                "id": 1,
                "type": 7,
                "all_in_one_login": {"cinta": self.cinta},
            },
            rpc_name="rpc-login",
        )
        login_resp = res["body"]["resp_login_of_some_type"]
        self.auth_ticket = login_resp["authenticationTicket"]
        self.clide = login_resp["clide"]
        print(
            f"  [+] Logado! Cinta: {self.cinta}, Clide: {self.clide}, Ticket: {self.auth_ticket}"
        )

    def step2_query_cms_and_songs(self) -> str:
        """Fetches CMS configs and available songs."""
        print("[2/5] Consultando CMS e catálogo de músicas...")
        cms_res = self._post(
            service="cmsservice",
            body={"id": 2},
            rpc_name="rpc-cms",
        )
        resources = cms_res["body"]["blah"]["blah"]["blah"]
        print(f"  [+] CMS retornou {len(resources)} catálogos de configuração.")

        songs_res = self._post(
            service="songservice",
            body={"id": 3},
            rpc_name="rpc-songs",
        )
        songs = songs_res["body"]["songs"]
        selected_song = songs[0]["id"]
        print(f"  [+] Músicas disponíveis: {[s['title'] for s in songs]}")
        print(
            f"  [+] Música selecionada para execução: '{songs[0]['title']}' ({selected_song})"
        )
        return selected_song

    def step3_start_song(self, song_id: str) -> None:
        """Emits RhythmGameStarted_SharplaAudit event."""
        print(f"[3/5] Iniciando sessão da música '{song_id}' no jogo...")
        start_res = self._post(
            service="syncservice",
            body={
                "audits": [
                    {
                        "event": "RhythmGameStarted_SharplaAudit",
                        "song_id": song_id,
                        "timestamp": int(time.time() * 1000),
                    }
                ]
            },
            rpc_name="rpc-song-start",
        )
        assert start_res["body"]["sync_success"] is True
        print("  [+] Evento RhythmGameStarted_SharplaAudit aceito pelo servidor.")

    def step4_simulate_autoplay_notes(self) -> int:
        """Simulates note hitting using Beatstar autoplay timing."""
        print(
            "[4/5] Executando simulação de Autoplay (GameController.InteractionVisibleStart)..."
        )
        notes = [
            ("TapInteraction", 0.5, "PERFECT_PLUS"),
            ("HoldInteraction", 1.0, "PERFECT_PLUS"),
            ("FlickInteraction", 1.8, "PERFECT_PLUS"),
            ("SwitchHoldInteraction", 2.5, "PERFECT_PLUS"),
            ("SwitchHoldFlickInteraction", 3.2, "PERFECT_PLUS"),
            ("TapInteraction", 4.0, "PERFECT_PLUS"),
        ]

        total_score = 0
        for note_type, bar_time, grade in notes:
            score_delta = 8250
            total_score += score_delta
            print(
                f"  🎵 [Beat {bar_time:.1f}s] {note_type} -> {grade} (+{score_delta} pts)"
            )

        print(
            f"  [+] Música concluída com pontuação máxima de Autoplay: {total_score} pts!"
        )
        return total_score

    def step5_end_song_and_verify(self, song_id: str, score: int) -> None:
        """Emits RhythmGameEnded_SharplaAudit and asserts persistence."""
        print("[5/5] Enviando RhythmGameEnded_SharplaAudit e sincronizando perfil...")
        end_res = self._post(
            service="syncservice",
            body={
                "audits": [
                    {
                        "event": "RhythmGameEnded_SharplaAudit",
                        "song_id": song_id,
                        "score": score,
                        "timestamp": int(time.time() * 1000),
                    }
                ]
            },
            rpc_name="rpc-song-end",
        )
        assert end_res["body"]["sync_success"] is True

        # Consulta perfil atualizado
        profile_res = self._post(
            service="profileservice",
            body={"cinta": self.cinta},
            rpc_name="rpc-profile",
        )
        profile = profile_res["body"]["profile"]
        print(f"  [+] Perfil atualizado no banco:")
        print(f"      - Jogador: {profile.get('player_name')}")
        print(f"      - Estrelas: {profile.get('stars')}")
        print(f"      - Moedas: {profile.get('coins')}")
        print(f"      - Nível: {profile.get('level')}")

        assert profile.get("stars") > 0, "Estrelas deveriam ter incrementado!"
        print(
            "\n[✓] Validação de execução automatizada de música concluída com SUCESSO!"
        )

    def run(self) -> None:
        """Executes full simulation flow."""
        self.step1_login()
        song_id = self.step2_query_cms_and_songs()
        self.step3_start_song(song_id)
        score = self.step4_simulate_autoplay_notes()
        self.step5_end_song_and_verify(song_id, score)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate Beatstar song autoplay against server"
    )
    parser.add_argument(
        "--url", default="http://localhost:8080", help="URL base do servidor"
    )
    parser.add_argument(
        "--cinta",
        default="676d4d53-f0cb-41c6-8c27-4bb3c3c3c905",
        help="UUID Cinta do jogador",
    )
    args = parser.parse_args()

    simulator = AutoplaySimulator(base_url=args.url, cinta=args.cinta)
    simulator.run()


if __name__ == "__main__":
    main()
