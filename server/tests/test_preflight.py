import pytest
from server.services.preflight_service import PreflightValidator

def test_preflight_validator_missing_endpoint():
    validator = PreflightValidator(server_url="", adb_serial="emulator-5554", apk_path="nonexistent.apk")
    result = validator.check_all()
    assert result.success is False
    assert any("server url" in err.lower() for err in result.errors)

def test_preflight_validator_invalid_apk():
    validator = PreflightValidator(server_url="http://localhost:8080", adb_serial="emulator-5554", apk_path="nonexistent.apk")
    result = validator.check_all()
    assert result.success is False
    assert any("apk path" in err.lower() for err in result.errors)
