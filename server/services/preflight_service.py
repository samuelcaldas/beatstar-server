from dataclasses import dataclass, field
from typing import List
import os
import urllib.request
import urllib.error

@dataclass
class PreflightResult:
    success: bool
    errors: List[str] = field(default_factory=list)

class PreflightValidator:
    def __init__(self, server_url: str, adb_serial: str, apk_path: str):
        self.server_url = server_url
        self.adb_serial = adb_serial
        self.apk_path = apk_path

    def check_all(self) -> PreflightResult:
        errors = []
        if not self.server_url:
            errors.append("Server URL is required.")
        else:
            try:
                health_url = f"{self.server_url.rstrip('/')}/health"
                req = urllib.request.Request(health_url, headers={"User-Agent": "BeatstarPreflight/1.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status != 200:
                        errors.append(f"Server health endpoint returned status {resp.status}")
            except Exception as e:
                errors.append(f"Failed to reach server health endpoint at {self.server_url}: {e}")

        if not self.adb_serial:
            errors.append("ADB serial is required.")

        if not self.apk_path or not os.path.exists(self.apk_path):
            errors.append(f"APK path invalid or missing: {self.apk_path}")

        return PreflightResult(success=len(errors) == 0, errors=errors)
