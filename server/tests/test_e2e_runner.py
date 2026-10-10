import pytest
from pathlib import Path
from scripts.run_onboarding_e2e import E2ERunner

def test_e2e_runner_initialization():
    runner = E2ERunner(
        adb_serial="emulator-5554",
        server_url="http://localhost:8080",
        apk_path=Path("nonexistent.apk"),
        output_dir=Path(".playwright-mcp/test_run")
    )
    assert runner.adb_serial == "emulator-5554"
    assert runner.server_url == "http://localhost:8080"
