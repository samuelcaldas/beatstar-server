#!/usr/bin/env python3
"""APK Patching Tool for Beatstar.

Decompiles APK resources with Apktool, injects permissive network-security-config.xml,
configures debug mode, patches metadata gateway host and libil2cpp port, signs with apksigner.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from scripts.patch_ads_metadata import MetadataAdPatcher
    from scripts.patch_il2cpp import Il2CppBinaryPatcher
except ImportError:
    from patch_ads_metadata import MetadataAdPatcher
    from patch_il2cpp import Il2CppBinaryPatcher


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

    def enable_debugging(self) -> None:
        content = self._read_manifest()
        match = re.search(r"<application\b([^>]*)>", content)
        if not match:
            raise RuntimeError("Tag <application> não encontrada!")
        attrs = match.group(1)
        attrs, replacements = re.subn(
            r'\bandroid:debuggable\s*=\s*"[^"]*"',
            'android:debuggable="true"',
            attrs,
            count=1,
        )
        if replacements == 0:
            attrs += ' android:debuggable="true"'
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


class ApkSignerHelper:
    """Manages debug keystore generation, zipalign, and apksigner."""

    def __init__(self, tools_dir: Path) -> None:
        self.tools_dir = tools_dir.resolve()
        self.keystore = self._ensure_keystore()

    def _ensure_keystore(self) -> Path:
        keystore_path = self.tools_dir / "debug.keystore"
        if keystore_path.exists():
            return keystore_path
        print("[*] Gerando debug keystore...")
        cmd_key = [
            "keytool", "-genkeypair", "-v", "-keystore", str(keystore_path),
            "-alias", "androiddebugkey", "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-storepass", "android", "-keypass", "android",
            "-dname", "CN=Android Debug,O=Android,C=US",
        ]
        subprocess.run(cmd_key, check=True, capture_output=True)
        return keystore_path

    def align_and_sign(self, unsigned_apk: Path, output_apk: Path) -> None:
        """Runs zipalign and apksigner for V2/V3 signature schemes."""
        aligned_apk = unsigned_apk.parent / f"aligned_{unsigned_apk.name}"
        if aligned_apk.exists():
            aligned_apk.unlink()
        cmd_align = ["zipalign", "-p", "-f", "4", str(unsigned_apk), str(aligned_apk)]
        subprocess.run(cmd_align, check=True, capture_output=True)
        cmd_sign = [
            "apksigner", "sign", "--ks", str(self.keystore),
            "--ks-pass", "pass:android", "--key-pass", "pass:android",
            "--ks-key-alias", "androiddebugkey", "--out", str(output_apk),
            str(aligned_apk),
        ]
        subprocess.run(cmd_sign, check=True, capture_output=True)
        if aligned_apk.exists():
            aligned_apk.unlink()


class SplitApkPatcher:
    """Patches native library port in split config APK."""

    def __init__(self, split_path: Path, port: int, signer: ApkSignerHelper) -> None:
        self.split_path = split_path.resolve()
        self.port = port
        self.signer = signer

    def patch_and_sign(self, output_path: Path) -> None:
        """Extracts libil2cpp.so, patches port instruction, and repackages split APK."""
        print(f"[*] Aplicando patch de porta ({self.port}) no split {self.split_path.name}...")
        work_dir = output_path.parent / "split_work"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.split_path, "r") as zf:
            zf.extractall(work_dir)
        so_path = work_dir / "lib" / "arm64-v8a" / "libil2cpp.so"
        if so_path.exists():
            patcher = Il2CppBinaryPatcher(so_path)
            patcher.patch_port(port=self.port)
        unsigned = output_path.parent / "unsigned_split.apk"
        self._create_zip(work_dir, unsigned)
        self.signer.align_and_sign(unsigned, output_path)
        if unsigned.exists():
            unsigned.unlink()
        shutil.rmtree(work_dir)
        print(f"[✓] Split APK gerado com sucesso: {output_path}")

    @staticmethod
    def _create_zip(source_dir: Path, target_zip: Path) -> None:
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = full_p.relative_to(source_dir)
                    zf.write(full_p, arcname)


class BaseApkPatcher:
    """Decodes, modifies and rebuilds base Beatstar APK."""

    def __init__(
        self,
        apk_path: Path,
        output_apk: Path,
        tools_dir: Path,
        patch_dir: Path,
        host: str = "192.168.1.68",
        signer: ApkSignerHelper | None = None,
    ) -> None:
        self.apk_path = apk_path.resolve()
        self.output_apk = output_apk.resolve()
        self.tools_dir = tools_dir.resolve()
        self.patch_dir = patch_dir.resolve()
        self.host = host
        self.signer = signer
        self.apktool_jar = self.tools_dir / "apktool" / "apktool.jar"
        self.work_dir = self.output_apk.parent / "base_patch_work"

    def decode_apk(self) -> None:
        print(f"[*] Decodificando recursos de {self.apk_path.name}...")
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        cmd = ["java", "-jar", str(self.apktool_jar), "d", "-f", "-s", str(self.apk_path), "-o", str(self.work_dir)]
        subprocess.run(cmd, check=True, capture_output=True)

    def inject_modifications(self) -> None:
        print("[*] Injetando network_security_config e modo debuggable...")
        res_xml = self.work_dir / "res" / "xml"
        res_xml.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.patch_dir / "network_security_config.xml", res_xml / "network_security_config.xml")
        patcher = ManifestPatcher(self.work_dir / "AndroidManifest.xml")
        patcher.enable_cleartext_traffic()
        patcher.enable_debugging()
        self._patch_metadata()

    def _patch_metadata(self) -> None:
        meta_p = self.work_dir / "assets" / "bin" / "Data" / "Managed" / "Metadata" / "global-metadata.dat"
        if not meta_p.exists():
            raise FileNotFoundError(f"global-metadata.dat não encontrado: {meta_p}")
        print(f"[*] Aplicando patch de gateway host ({self.host}) no global-metadata.dat...")
        meta_patcher = MetadataAdPatcher(meta_p)
        if not meta_patcher.patch(socket_gateway_host=self.host):
            raise ValueError(f"Gateway host não foi alterado para {self.host!r}")

    def build_and_sign(self) -> None:
        print("[*] Reconstruindo base APK com Apktool...")
        if self.signer is None:
            self.signer = ApkSignerHelper(self.tools_dir)
        unsigned = self.output_apk.parent / "unsigned_base.apk"
        cmd_b = ["java", "-jar", str(self.apktool_jar), "b", str(self.work_dir), "-o", str(unsigned)]
        subprocess.run(cmd_b, check=True, capture_output=True)
        self.signer.align_and_sign(unsigned, self.output_apk)
        if unsigned.exists():
            unsigned.unlink()
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        print(f"[✓] Base APK gerado com sucesso: {self.output_apk}")

    def run(self) -> None:
        self.decode_apk()
        self.inject_modifications()
        self.build_and_sign()


class ApkPatcher(BaseApkPatcher):
    """Compatibility facade for the pre-split APK patcher API."""

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
        server_url: str | None = None,
    ) -> None:
        """Preserve legacy construction while routing to the base APK patcher."""
        super().__init__(
            apk_path=apk_path,
            output_apk=output_apk,
            tools_dir=tools_dir,
            patch_dir=patch_dir,
            host=server_url or "192.168.1.68",
        )
        self.server_url = server_url
        self.ads_app_id = ads_app_id
        self.enable_ads = enable_ads
        self.rewarded_ad_unit = rewarded_ad_unit
        self.interstitial_ad_unit = interstitial_ad_unit


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar APK & Split Patcher")
    parser.add_argument("--apk", type=Path, required=True, help="Path para base.apk")
    parser.add_argument("--split-apk", type=Path, default=None, help="Path para split_config.arm64_v8a.apk")
    parser.add_argument("--host", type=str, default="192.168.1.68", help="IP do servidor na LAN")
    parser.add_argument("--port", type=int, default=9090, help="Porta TCP do SocketGateway")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"), help="Diretório de saída")
    parser.add_argument("--tools-dir", type=Path, default=Path("tools"), help="Diretório de ferramentas")
    parser.add_argument("--patch-dir", type=Path, default=Path("client_patch"), help="Diretório de patches")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    signer = ApkSignerHelper(args.tools_dir)
    base_out = args.output_dir / "base-patched.apk"
    base_patcher = BaseApkPatcher(
        apk_path=args.apk, output_apk=base_out, tools_dir=args.tools_dir,
        patch_dir=args.patch_dir, host=args.host, signer=signer,
    )
    base_patcher.run()

    if args.split_apk and args.split_apk.exists():
        split_out = args.output_dir / "split_config.arm64_v8a-patched.apk"
        split_patcher = SplitApkPatcher(args.split_apk, port=args.port, signer=signer)
        split_patcher.patch_and_sign(split_out)


if __name__ == "__main__":
    main()
