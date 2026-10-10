import pytest
from pathlib import Path
from scripts.patch_apk import ApkPatcher

def test_apk_patcher_init():
    patcher = ApkPatcher(
        apk_path=Path("nonexistent.apk"),
        output_apk=Path("dist/output.apk"),
        tools_dir=Path("tools"),
        patch_dir=Path("client_patch"),
        server_url="http://10.0.2.2:8080"
    )
    assert patcher.server_url == "http://10.0.2.2:8080"
