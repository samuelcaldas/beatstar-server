#!/usr/bin/env python3
"""APK Patching Tool for Beatstar.

Decompiles APK resources with Apktool, injects permissive network-security-config.xml,
configures Google Ads App ID, patches metadata ad unit IDs, rebuilds and signs APK.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from scripts.patch_ads_metadata import MetadataAdPatcher
except ImportError:
    from patch_ads_metadata import MetadataAdPatcher


class ManifestPatcher:
    """Handles XML modifications for AndroidManifest.xml."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path

    def _read_manifest(self) -> str:
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_manifest(self, content: str) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write(content)

    def enable_cleartext_traffic(self) -> None:
        content = self._read_manifest()
        match = re.search(r"<application\b([^>]*)>", content)
        if not match:
            raise RuntimeError("Tag <application> não encontrada!")
        attrs = match.group(1)
        if "networkSecurityConfig" not in attrs:
            attrs += ' android:networkSecurityConfig="@xml/network_security_config"'
        if "usesCleartextTraffic" not in attrs:
            attrs += ' android:usesCleartextTraffic="true"'
        new_content = (
            content[: match.start()] + f"<application{attrs}>" + content[match.end() :]
        )
        self._write_manifest(new_content)

    def set_google_ads_app_id(self, app_id: str) -> None:
        content = self._read_manifest()
        pattern = r'(<meta-data\s+android:name="com\.google\.android\.gms\.ads\.APPLICATION_ID"\s+android:value=")[^"]*(")'
        if not re.search(pattern, content):
            return
        new_content = re.sub(pattern, rf"\g<1>{app_id}\g<2>", content)
        self._write_manifest(new_content)


class ApkPatcher:
    """Automates decoding, modifying, building, and signing Android APK."""

    def __init__(
        self,
        apk_path: Path,
        output_apk: Path,
        tools_dir: Path,
        patch_dir: Path,
        ads_app_id: str | None = None,
        enable_ads: bool = True,
        rewarded_ad_unit: str | None = None,
        interstitial_ad_unit: str | None = None,
    ):
        self.apk_path = apk_path.resolve()
        self.output_apk = output_apk.resolve()
        self.tools_dir = tools_dir.resolve()
        self.patch_dir = patch_dir.resolve()
        self.ads_app_id = ads_app_id
        self.enable_ads = enable_ads
        self.rewarded_ad_unit = rewarded_ad_unit
        self.interstitial_ad_unit = interstitial_ad_unit
        self.apktool_jar = self.tools_dir / "apktool" / "apktool.jar"
        self.work_dir = self.output_apk.parent / "apk_patch_work"

    def validate(self) -> None:
        if not self.apk_path.exists():
            raise FileNotFoundError(f"APK não encontrado: {self.apk_path}")
        if not self.apktool_jar.exists():
            raise FileNotFoundError(
                f"Apktool não encontrado em {self.apktool_jar}."
            )

    def decode_apk(self) -> None:
        print(f"[*] Decodificando recursos de {self.apk_path.name} com Apktool...")
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        cmd = [
            "java",
            "-jar",
            str(self.apktool_jar),
            "d",
            "-f",
            "-s",
            str(self.apk_path),
            "-o",
            str(self.work_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao decodificar APK:\n{proc.stderr}")
        print("[+] Recursos decodificados com sucesso!")

    def inject_network_security(self) -> None:
        print("[*] Injetando network_security_config.xml...")
        res_xml = self.work_dir / "res" / "xml"
        res_xml.mkdir(parents=True, exist_ok=True)
        config_source = self.patch_dir / "network_security_config.xml"
        shutil.copy(config_source, res_xml / "network_security_config.xml")
        patcher = ManifestPatcher(self.work_dir / "AndroidManifest.xml")
        patcher.enable_cleartext_traffic()
        print("[+] AndroidManifest.xml atualizado com segurança permissiva!")

    def inject_ads_configuration(self) -> None:
        if not self.ads_app_id:
            return
        print(f"[*] Injetando Google Ads App ID: {self.ads_app_id}...")
        patcher = ManifestPatcher(self.work_dir / "AndroidManifest.xml")
        patcher.set_google_ads_app_id(self.ads_app_id)
        print("[+] Google Ads App ID injetado com sucesso no Manifest!")

    def patch_metadata_ad_units(self) -> None:
        if not self.rewarded_ad_unit and not self.interstitial_ad_unit:
            return
        meta_path = (
            self.work_dir
            / "assets"
            / "bin"
            / "Data"
            / "Managed"
            / "Metadata"
            / "global-metadata.dat"
        )
        if not meta_path.exists():
            return
        print("[*] Aplicando patch de Ad Units no global-metadata.dat...")
        ad_patcher = MetadataAdPatcher(meta_path)
        ad_patcher.patch(
            rewarded_id=self.rewarded_ad_unit,
            interstitial_id=self.interstitial_ad_unit,
        )
        print("[+] Ad Units patched no global-metadata.dat!")

    def _ensure_keystore(self) -> Path:
        keystore_path = self.tools_dir / "debug.keystore"
        if keystore_path.exists():
            return keystore_path
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
        return keystore_path

    def build_and_sign(self) -> None:
        print("[*] Reconstruindo APK com Apktool...")
        unsigned_apk = self.work_dir.parent / "unsigned.apk"
        cmd_b = [
            "java",
            "-jar",
            str(self.apktool_jar),
            "b",
            str(self.work_dir),
            "-o",
            str(unsigned_apk),
        ]
        proc = subprocess.run(cmd_b, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Falha ao reconstruir APK:\n{proc.stderr}")
        keystore = self._ensure_keystore()
        print("[*] Assinando APK...")
        cmd_sign = [
            "jarsigner",
            "-verbose",
            "-sigalg",
            "SHA256withRSA",
            "-digestalg",
            "SHA-256",
            "-keystore",
            str(keystore),
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
        print(f"[✓] APK gerado com sucesso em: {self.output_apk}")

    def run(self) -> None:
        self.validate()
        self.decode_apk()
        self.inject_network_security()
        self.inject_ads_configuration()
        self.patch_metadata_ad_units()
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
    parser.add_argument(
        "--ads-app-id", type=str, default=None, help="Google Ads / AdMob App ID"
    )
    parser.add_argument(
        "--enable-ads",
        action="store_true",
        default=True,
        help="Habilita sistema de anúncios",
    )
    parser.add_argument(
        "--disable-ads",
        dest="enable_ads",
        action="store_false",
        help="Desabilita anúncios",
    )
    parser.add_argument(
        "--rewarded-ad-unit",
        type=str,
        default=None,
        help="Custom rewarded ad unit ID",
    )
    parser.add_argument(
        "--interstitial-ad-unit",
        type=str,
        default=None,
        help="Custom interstitial ad unit ID",
    )
    args = parser.parse_args()

    patcher = ApkPatcher(
        apk_path=args.apk,
        output_apk=args.output_apk,
        tools_dir=args.tools_dir,
        patch_dir=args.patch_dir,
        ads_app_id=args.ads_app_id,
        enable_ads=args.enable_ads,
        rewarded_ad_unit=args.rewarded_ad_unit,
        interstitial_ad_unit=args.interstitial_ad_unit,
    )
    patcher.run()


if __name__ == "__main__":
    main()
