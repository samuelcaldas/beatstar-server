#!/usr/bin/env python3
"""APK Patching Tool for Beatstar.

Decompiles APK resources with Apktool, injects permissive network-security-config.xml,
enables cleartext HTTP traffic, rebuilds the APK, and signs it with a debug keystore.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


class ApkPatcher:
    """Automates decoding, modifying, building, and signing Android APK."""

    def __init__(
        self, apk_path: Path, output_apk: Path, tools_dir: Path, patch_dir: Path
    ):
        self.apk_path = apk_path.resolve()
        self.output_apk = output_apk.resolve()
        self.tools_dir = tools_dir.resolve()
        self.patch_dir = patch_dir.resolve()
        self.apktool_jar = self.tools_dir / "apktool" / "apktool.jar"
        self.work_dir = self.output_apk.parent / "apk_patch_work"

    def validate(self) -> None:
        """Validates prerequisites."""
        if not self.apk_path.exists():
            raise FileNotFoundError(f"APK não encontrado: {self.apk_path}")
        if not self.apktool_jar.exists():
            raise FileNotFoundError(
                f"Apktool não encontrado em {self.apktool_jar}. Execute scripts/setup_tools.sh primeiro."
            )

    def decode_apk(self) -> None:
        """Decodes APK with apktool preserving DEX files for speed."""
        print(f"[*] Decodificando recursos de {self.apk_path.name} com Apktool...")
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        cmd = [
            "java",
            "-jar",
            str(self.apktool_jar),
            "d",
            "-f",
            "-s",  # Don't decode sources/dex (keeps it fast)
            str(self.apk_path),
            "-o",
            str(self.work_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao decodificar APK:\n{proc.stderr}")
        print("[+] Recursos decodificados com sucesso!")

    def inject_network_security(self) -> None:
        """Copies network_security_config.xml and modifies AndroidManifest.xml."""
        print("[*] Injetando network_security_config.xml...")
        res_xml = self.work_dir / "res" / "xml"
        res_xml.mkdir(parents=True, exist_ok=True)

        config_source = self.patch_dir / "network_security_config.xml"
        shutil.copy(config_source, res_xml / "network_security_config.xml")

        manifest = self.work_dir / "AndroidManifest.xml"
        with open(manifest, "r", encoding="utf-8") as f:
            content = f.read()

        # Adiciona networkSecurityConfig e usesCleartextTraffic na tag <application
        app_tag_match = re.search(r"<application\b([^>]*)>", content)
        if not app_tag_match:
            raise RuntimeError(
                "Tag <application> não encontrada no AndroidManifest.xml!"
            )

        attrs = app_tag_match.group(1)
        if "networkSecurityConfig" not in attrs:
            attrs += ' android:networkSecurityConfig="@xml/network_security_config"'
        if "usesCleartextTraffic" not in attrs:
            attrs += ' android:usesCleartextTraffic="true"'

        new_manifest = (
            content[: app_tag_match.start()]
            + f"<application{attrs}>"
            + content[app_tag_match.end() :]
        )
        with open(manifest, "w", encoding="utf-8") as f:
            f.write(new_manifest)
        print("[+] AndroidManifest.xml atualizado com segurança permissiva!")

    def build_and_sign(self) -> None:
        """Rebuilds APK and signs it with debug keystore."""
        print("[*] Reconstruindo APK com Apktool...")
        unsigned_apk = self.work_dir.parent / "unsigned.apk"
        cmd_build = [
            "java",
            "-jar",
            str(self.apktool_jar),
            "b",
            str(self.work_dir),
            "-o",
            str(unsigned_apk),
        ]
        proc = subprocess.run(cmd_build, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao reconstruir APK:\n{proc.stderr}")

        keystore_path = self.tools_dir / "debug.keystore"
        if not keystore_path.exists():
            print("[*] Gerando debug keystore...")
            cmd_key = [
                "keytool",
                "-genkeypair",
                "-v",
                "-keystore",
                str(keystore_path),
                "-alias",
                "androiddebugkey",
                "-keyalg",
                "RSA",
                "-keysize",
                "2048",
                "-validity",
                "10000",
                "-storepass",
                "android",
                "-keypass",
                "android",
                "-dname",
                "CN=Android Debug,O=Android,C=US",
            ]
            subprocess.run(cmd_key, check=True, capture_output=True)

        print("[*] Assinando APK...")
        cmd_sign = [
            "jarsigner",
            "-verbose",
            "-sigalg",
            "SHA256withRSA",
            "-digestalg",
            "SHA-256",
            "-keystore",
            str(keystore_path),
            "-storepass",
            "android",
            str(unsigned_apk),
            "androiddebugkey",
        ]
        subprocess.run(cmd_sign, check=True, capture_output=True)

        self.output_apk.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(unsigned_apk), str(self.output_apk))
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        print(f"[✓] APK modificado e assinado gerado com sucesso em: {self.output_apk}")

    def run(self) -> None:
        """Runs complete patch workflow."""
        self.validate()
        self.decode_apk()
        self.inject_network_security()
        self.build_and_sign()


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar APK Patcher")
    parser.add_argument("--apk", type=Path, required=True, help="Caminho do APK base")
    parser.add_argument(
        "--output-apk",
        type=Path,
        default=Path("dist/beatstar-patched.apk"),
        help="Caminho do APK de saída",
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path("tools"),
        help="Diretório de ferramentas",
    )
    parser.add_argument(
        "--patch-dir",
        type=Path,
        default=Path("client_patch"),
        help="Diretório de patches",
    )
    args = parser.parse_args()

    patcher = ApkPatcher(
        apk_path=args.apk,
        output_apk=args.output_apk,
        tools_dir=args.tools_dir,
        patch_dir=args.patch_dir,
    )
    patcher.run()


if __name__ == "__main__":
    main()
