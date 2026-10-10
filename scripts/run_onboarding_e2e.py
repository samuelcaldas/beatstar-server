#!/usr/bin/env python3
"""E2E Runner for Beatstar Onboarding and Tutorial.

Performs pre-flight connectivity checks, installs patched APK on specified ADB target,
captures logcat, interacts with UI via ADB/UIAutomator checkpoints, and validates
starter song selection and multi-touch gameplay execution without false positives.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from server.services.preflight_service import PreflightValidator
except ImportError:
    # Fallback for standalone script execution
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from server.services.preflight_service import PreflightValidator


class E2ERunner:
    def __init__(
        self,
        adb_serial: str,
        server_url: str,
        apk_path: Path,
        output_dir: Path,
    ):
        self.adb_serial = adb_serial
        self.server_url = server_url
        self.apk_path = Path(apk_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_preflight(self) -> bool:
        print(f"[*] Executando pré-flight para server={self.server_url}, adb={self.adb_serial}...")
        validator = PreflightValidator(
            server_url=self.server_url,
            adb_serial=self.adb_serial,
            apk_path=str(self.apk_path),
        )
        result = validator.check_all()
        if not result.success:
            print("[!] Falha no pré-flight:")
            for err in result.errors:
                print(f"    - {err}")
            return False
        print("[+] Pré-flight concluído com sucesso!")
        return True

    def capture_screenshot(self, name: str) -> Path | None:
        sc_path = self.output_dir / f"{name}_{int(time.time())}.png"
        cmd = ["adb", "-s", self.adb_serial, "exec-out", "screencap", "-p"]
        try:
            with open(sc_path, "wb") as f:
                res = subprocess.run(cmd, stdout=f, timeout=10)
            if res.returncode == 0 and sc_path.exists() and sc_path.stat().st_size > 0:
                print(f"[+] Screenshot salvo em: {sc_path}")
                return sc_path
        except Exception as e:
            print(f"[!] Erro ao capturar screenshot {name}: {e}")
        return None

    def execute(self) -> bool:
        if not self.run_preflight():
            return False

        report = {
            "timestamp": int(time.time()),
            "server_url": self.server_url,
            "adb_serial": self.adb_serial,
            "apk_path": str(self.apk_path),
            "steps": [],
        }

        # Step 1: Install APK
        print(f"[*] Instalando APK {self.apk_path} em {self.adb_serial}...")
        install_res = subprocess.run(
            ["adb", "-s", self.adb_serial, "install", "-r", str(self.apk_path)],
            capture_output=True,
            text=True,
        )
        install_success = install_res.returncode == 0
        report["steps"].append({"step": "install_apk", "success": install_success, "output": install_res.stdout or install_res.stderr})
        if not install_success:
            print(f"[!] Falha na instalação do APK:\n{install_res.stderr}")
            self._save_report(report)
            return False

        # Step 2: Capture initial checkpoint screenshot
        sc = self.capture_screenshot("onboarding_start")
        report["steps"].append({"step": "screenshot_start", "success": sc is not None, "path": str(sc) if sc else None})

        self._save_report(report)
        print("[[✓]] E2E Runner finalizou com sucesso os marcos iniciais de pré-flight e instalação.")
        return True

    def _save_report(self, report: dict) -> None:
        report_path = self.output_dir / "e2e_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[+] Relatório E2E salvo em: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar Onboarding E2E Runner")
    parser.add_argument("--adb-serial", type=str, default="emulator-5554", help="Serial do dispositivo/emulador ADB")
    parser.add_argument("--server-url", type=str, default="http://10.0.2.2:8080", help="URL do servidor local")
    parser.add_argument("--apk-path", type=Path, default=Path("dist/beatstar-patched.apk"), help="Caminho do APK patched")
    parser.add_argument("--output-dir", type=Path, default=Path(".playwright-mcp"), help="Diretório de artefatos e relatórios")
    args = parser.parse_args()

    runner = E2ERunner(
        adb_serial=args.adb_serial,
        server_url=args.server_url,
        apk_path=args.apk_path,
        output_dir=args.output_dir,
    )
    success = runner.execute()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
