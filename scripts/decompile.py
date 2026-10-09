#!/usr/bin/env python3
"""Automated decompilation pipeline for Beatstar (Space Ape Games - Flamingo).

Extracts APKM bundles, unpacks Unity IL2CPP assets (metadata v31, libil2cpp.so),
executes Il2CppDumper, decompiles C# dummy assemblies with ilspycmd,
and decompiles Android DEX with JADX.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


class DecompilationError(Exception):
    """Raised when any step of the decompilation pipeline fails."""


class DecompilePipeline:
    """Manages the full APK extraction, dumping, and decompilation process."""

    KEY_ASSEMBLIES = [
        "Assembly-CSharp.dll",
        "SharplaClient.dll",
        "SharplaModel.dll",
        "SharplaShared.dll",
        "SpaceApe.Network.dll",
        "SpaceApe.Network.Serializer.dll",
        "SpaceApe.Rpc.dll",
        "SpaceApe.Login.Runtime.dll",
        "MetaLogic.dll",
        "RakshaModel.dll",
    ]

    def __init__(
        self,
        apkm_path: Path,
        output_dir: Path,
        tools_dir: Path,
        arch: str = "arm64-v8a",
    ):
        self.apkm_path = apkm_path.resolve()
        self.output_dir = output_dir.resolve()
        self.tools_dir = tools_dir.resolve()
        self.arch = arch

        self.extracted_dir = self.output_dir / "extracted"
        self.il2cpp_out_dir = self.output_dir / "il2cpp"
        self.csharp_dir = self.output_dir / "csharp"
        self.java_dir = self.output_dir / "java"
        self.assets_dir = self.output_dir / "assets"

    def validate_inputs(self) -> None:
        """Validates existence of input APK/APKM and tooling before proceeding."""
        if not self.apkm_path.exists():
            raise DecompilationError(
                f"Arquivo APK/APKM não encontrado: {self.apkm_path}"
            )

        dumper_dll = self.tools_dir / "Il2CppDumper" / "Il2CppDumper.dll"
        if not dumper_dll.exists():
            raise DecompilationError(
                f"Il2CppDumper não encontrado em {dumper_dll}. Execute scripts/setup_tools.sh primeiro."
            )

    def extract_apkm(self) -> tuple[Path, Path]:
        """Extracts base.apk and the arch split APK from the APKM bundle."""
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        base_apk = self.extracted_dir / "base.apk"
        split_apk = (
            self.extracted_dir / f"split_config.{self.arch.replace('-', '_')}.apk"
        )

        print(f"[*] Extraindo pacotes de {self.apkm_path.name}...")
        with zipfile.ZipFile(self.apkm_path, "r") as z:
            namelist = z.namelist()
            if "base.apk" in namelist:
                with z.open("base.apk") as src, open(base_apk, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            else:
                base_apk = self.apkm_path

            split_name = f"split_config.{self.arch.replace('-', '_')}.apk"
            if split_name in namelist:
                with z.open(split_name) as src, open(split_apk, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            else:
                split_apk = base_apk

        return base_apk, split_apk

    def extract_il2cpp_files(
        self, base_apk: Path, split_apk: Path
    ) -> tuple[Path, Path]:
        """Extracts libil2cpp.so and global-metadata.dat from APKs."""
        il2cpp_bin_dir = self.extracted_dir / "il2cpp_bin"
        il2cpp_bin_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = il2cpp_bin_dir / "global-metadata.dat"
        so_path = il2cpp_bin_dir / "libil2cpp.so"

        print("[*] Extraindo global-metadata.dat de base.apk...")
        with zipfile.ZipFile(base_apk, "r") as z:
            meta_internal = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
            if meta_internal not in z.namelist():
                raise DecompilationError(
                    "global-metadata.dat não encontrado em base.apk!"
                )
            with z.open(meta_internal) as src, open(metadata_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

        print(f"[*] Extraindo libil2cpp.so para {self.arch}...")
        with zipfile.ZipFile(split_apk, "r") as z:
            so_internal = f"lib/{self.arch}/libil2cpp.so"
            if so_internal not in z.namelist():
                raise DecompilationError(
                    f"libil2cpp.so não encontrado para {self.arch}!"
                )
            with z.open(so_internal) as src, open(so_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

        return so_path, metadata_path

    def run_il2cpp_dumper(self, so_path: Path, metadata_path: Path) -> None:
        """Executes Il2CppDumper via dotnet runtime."""
        self.il2cpp_out_dir.mkdir(parents=True, exist_ok=True)
        dumper_dll = self.tools_dir / "Il2CppDumper" / "Il2CppDumper.dll"

        print(f"[*] Executando Il2CppDumper em {so_path.name}...")
        cmd = [
            "dotnet",
            "--roll-forward",
            "LatestMajor",
            str(dumper_dll),
            str(so_path),
            str(metadata_path),
            str(self.il2cpp_out_dir),
        ]
        proc = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise DecompilationError(
                f"Il2CppDumper falhou (código {proc.returncode}):\n{proc.stderr}"
            )
        print("[+] Il2CppDumper finalizado com sucesso!")

    def decompile_csharp_assemblies(self) -> None:
        """Decompiles key DummyDll assemblies using ilspycmd."""
        dummy_dll_dir = self.il2cpp_out_dir / "DummyDll"
        if not dummy_dll_dir.exists():
            print("[!] DummyDll não encontrado. Pulando descompilação C#.")
            return

        ilspy = shutil.which("ilspycmd")
        if not ilspy:
            print(
                "[!] 'ilspycmd' não encontrado no PATH. Instale com: dotnet tool install -g ilspycmd"
            )
            return

        self.csharp_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Descompilando assemblies C# com ilspycmd...")
        for dll_name in self.KEY_ASSEMBLIES:
            dll_path = dummy_dll_dir / dll_name
            if not dll_path.exists():
                continue
            out_subdir = self.csharp_dir / dll_name.replace(".dll", "")
            out_subdir.mkdir(parents=True, exist_ok=True)
            print(f"  -> Descompilando {dll_name}...")
            subprocess.run(
                [ilspy, "-p", "-o", str(out_subdir), str(dll_path)], capture_output=True
            )

    def decompile_java(self, base_apk: Path) -> None:
        """Decompiles Android DEX files using JADX CLI."""
        jadx_bin = self.tools_dir / "jadx" / "bin" / "jadx"
        if not jadx_bin.exists():
            print("[!] JADX não encontrado. Pulando descompilação Java.")
            return

        self.java_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Descompilando DEX com JADX...")
        cmd = [str(jadx_bin), "-d", str(self.java_dir), "--no-res", str(base_apk)]
        subprocess.run(cmd, capture_output=True)
        print("[+] Descompilação Java concluída!")

    def extract_game_configs(self, base_apk: Path) -> None:
        """Extracts JSON, XML, and boot configs from APK assets."""
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Extraindo configurações e metadados de assets...")
        with zipfile.ZipFile(base_apk, "r") as z:
            for item in z.namelist():
                if item.startswith("assets/") and any(
                    item.endswith(ext) for ext in [".json", ".xml", ".config", ".proto"]
                ):
                    target = self.assets_dir / item.replace("assets/", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(item) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        print("[+] Configurações extraídas com sucesso!")

    def run(self, skip_jadx: bool = False, skip_csharp: bool = False) -> None:
        """Executes the complete decompilation workflow."""
        self.validate_inputs()
        base_apk, split_apk = self.extract_apkm()
        so_path, metadata_path = self.extract_il2cpp_files(base_apk, split_apk)
        self.run_il2cpp_dumper(so_path, metadata_path)

        if not skip_csharp:
            self.decompile_csharp_assemblies()

        if not skip_jadx:
            self.decompile_java(base_apk)

        self.extract_game_configs(base_apk)
        print(f"\n[✓] Pipeline de descompilação concluído em: {self.output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar APKM Decompilation Pipeline")
    parser.add_argument(
        "--apkm", type=Path, required=True, help="Caminho para o arquivo .apkm ou .apk"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("decompiled"),
        help="Diretório de saída (padrão: decompiled)",
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path("tools"),
        help="Diretório das ferramentas (padrão: tools)",
    )
    parser.add_argument(
        "--arch",
        choices=["arm64-v8a", "armeabi-v7a"],
        default="arm64-v8a",
        help="Arquitetura de libil2cpp.so a extrair",
    )
    parser.add_argument(
        "--skip-jadx", action="store_true", help="Pular descompilação com JADX"
    )
    parser.add_argument(
        "--skip-csharp", action="store_true", help="Pular descompilação com ilspycmd"
    )

    args = parser.parse_args()

    try:
        pipeline = DecompilePipeline(
            apkm_path=args.apkm,
            output_dir=args.output_dir,
            tools_dir=args.tools_dir,
            arch=args.arch,
        )
        pipeline.run(skip_jadx=args.skip_jadx, skip_csharp=args.skip_csharp)
    except DecompilationError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
