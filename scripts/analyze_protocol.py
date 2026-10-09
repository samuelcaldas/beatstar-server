#!/usr/bin/env python3
"""Protocol Analyzer for Beatstar (Space Ape Games - Sharpla / Flamingo).

Scans decompiled dump.cs to extract command registries,
request/response pairs, audit events, headers, and fields.
Outputs JSON specification and Pydantic models for the Server Emulator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class CommandField:
    """Represents a field in an RPC command."""

    name: str
    type_name: str
    is_array: bool = False


@dataclass
class ProtocolCommand:
    """Represents an extracted Flamingo/Sharpla command."""

    name: str
    category: str
    base_class: str = ""
    pair_name: str = ""
    fields: list[CommandField] = field(default_factory=list)


class ProtocolAnalyzer:
    """Extracts protocol structure and generates protocol models."""

    def __init__(self, dump_file: Path, output_json: Path, pydantic_dir: Path):
        self.dump_file = dump_file.resolve()
        self.output_json = output_json.resolve()
        self.pydantic_dir = pydantic_dir.resolve()
        self.commands: dict[str, ProtocolCommand] = {}

    def parse_dump_cs(self) -> None:
        """Parses dump.cs looking for com.spaceape.flamingo.commands."""
        print(f"[*] Analisando comandos no dump: {self.dump_file}...")
        if not self.dump_file.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.dump_file}")

        with open(self.dump_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Regex flexível para capturar classes sob o namespace com.spaceape.flamingo.commands
        class_regex = re.compile(
            r"// Namespace: com\.spaceape\.flamingo\.commands\n"
            r"(?:\[.*?\]\n)*"
            r"public (?:class|struct) (\w+)(?:\s*:\s*([\w\.]+))?.*?\n"
            r"\{(?P<body>[^\}]+)\}",
            re.MULTILINE,
        )

        for match in class_regex.finditer(content):
            name = match.group(1)
            base_class = match.group(2) or ""
            body = match.group("body")

            if name.startswith("<") or "_Constructors" in name:
                continue

            category = self._categorize_command(name, base_class)
            fields = self._extract_fields(body)

            self.commands[name] = ProtocolCommand(
                name=name,
                category=category,
                base_class=base_class,
                fields=fields,
            )

        self._correlate_pairs()
        print(f"[+] Total de comandos mapeados: {len(self.commands)}")

    def _categorize_command(self, name: str, base_class: str) -> str:
        """Categorizes command based on naming conventions."""
        if name.endswith("_Req") or name.endswith("RpcReq") or name.endswith("Request"):
            return "request"
        if (
            name.endswith("_Resp")
            or name.endswith("RpcResp")
            or name.endswith("Response")
        ):
            return "response"
        if "Audit" in name or "Audit" in base_class:
            return "audit_event"
        if "Header" in name:
            return "header"
        return "data_model"

    def _extract_fields(self, body: str) -> list[CommandField]:
        """Extracts class fields from C# class body, ignoring constructors/types."""
        fields: list[CommandField] = []
        field_regex = re.compile(r"public\s+([\w<>\[\]\.]+)\s+(\w+);")
        for match in field_regex.finditer(body):
            type_name = match.group(1)
            f_name = match.group(2)
            if f_name in ("_Constructors", "<>9", "_ExternalTypeConstructors"):
                continue
            is_array = "[]" in type_name or "List<" in type_name
            fields.append(
                CommandField(name=f_name, type_name=type_name, is_array=is_array)
            )
        return fields

    def _correlate_pairs(self) -> None:
        """Correlates request commands with their corresponding response command."""
        for name, cmd in self.commands.items():
            if cmd.category == "request":
                expected_resp = name.replace("_Req", "_Resp").replace(
                    "RpcReq", "RpcResp"
                )
                if expected_resp in self.commands:
                    cmd.pair_name = expected_resp
                    self.commands[expected_resp].pair_name = name

    def export_json(self) -> None:
        """Exports parsed protocol commands to a JSON schema file."""
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(cmd) for name, cmd in sorted(self.commands.items())}
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[✓] Especificação JSON exportada em: {self.output_json}")

    def generate_pydantic_models(self) -> None:
        """Generates Pydantic models for the Server Emulator."""
        self.pydantic_dir.mkdir(parents=True, exist_ok=True)
        models_file = self.pydantic_dir / "generated_commands.py"
        init_file = self.pydantic_dir / "__init__.py"

        lines = [
            "# Auto-generated Pydantic Models from Beatstar IL2CPP Protocol",
            "from __future__ import annotations",
            "from typing import Any, Optional, list as ListType",
            "from pydantic import BaseModel, Field",
            "",
        ]

        for name, cmd in sorted(self.commands.items()):
            lines.append(f"class {name}(BaseModel):")
            lines.append(f'    """Category: {cmd.category}. Base: {cmd.base_class}"""')
            if not cmd.fields:
                lines.append("    pass\n")
                continue
            for f in cmd.fields:
                py_type = self._map_to_python_type(f.type_name)
                lines.append(f"    {f.name}: Optional[{py_type}] = None")
            lines.append("")

        with open(models_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        with open(init_file, "w", encoding="utf-8") as f:
            f.write("from .base_command import *\nfrom .generated_commands import *\n")

        print(f"[✓] Modelos Pydantic gerados em: {models_file}")

    def _map_to_python_type(self, cs_type: str) -> str:
        """Maps C# types to Python types."""
        clean = cs_type.replace("[]", "").replace("List<", "").replace(">", "").strip()
        mapping = {
            "int": "int",
            "long": "int",
            "uint": "int",
            "ulong": "int",
            "string": "str",
            "bool": "bool",
            "float": "float",
            "double": "float",
            "byte": "int",
        }
        res = mapping.get(clean, "Any")
        if "[]" in cs_type or "List<" in cs_type:
            return f"ListType[{res}]"
        return res


def main() -> None:
    parser = argparse.ArgumentParser(description="Beatstar Protocol Analyzer")
    parser.add_argument(
        "--dump",
        type=Path,
        required=True,
        help="Caminho para o arquivo dump.cs gerado pelo Il2CppDumper",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/sot/protocol_commands.json"),
        help="Caminho do arquivo JSON de saída",
    )
    parser.add_argument(
        "--pydantic-dir",
        type=Path,
        default=Path("server/models/protocol"),
        help="Diretório onde salvar os modelos Pydantic",
    )

    args = parser.parse_args()
    analyzer = ProtocolAnalyzer(
        dump_file=args.dump,
        output_json=args.output_json,
        pydantic_dir=args.pydantic_dir,
    )
    analyzer.parse_dump_cs()
    analyzer.export_json()
    analyzer.generate_pydantic_models()


if __name__ == "__main__":
    main()
