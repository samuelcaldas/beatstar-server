import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from scripts.patch_apk import BaseApkPatcher, ManifestPatcher
from scripts.patch_ads_metadata import MetadataAdPatcher


def test_manifest_patcher_enable_cleartext():
    sample_xml = '<manifest><application android:label="Beatstar"></application></manifest>'
    with tempfile.NamedTemporaryFile("w+", suffix=".xml", delete=False) as f:
        f.write(sample_xml)
        path = Path(f.name)

    try:
        patcher = ManifestPatcher(path)
        patcher.enable_cleartext_traffic()
        content = path.read_text()
        assert 'android:networkSecurityConfig="@xml/network_security_config"' in content
        assert 'android:usesCleartextTraffic="true"' in content
    finally:
        path.unlink(missing_ok=True)


def test_manifest_patcher_set_google_ads_app_id():
    sample_xml = (
        '<manifest><application>'
        '<meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" '
        'android:value="ca-app-pub-9249007709450981~3951571657"/>'
        '</application></manifest>'
    )
    with tempfile.NamedTemporaryFile("w+", suffix=".xml", delete=False) as f:
        f.write(sample_xml)
        path = Path(f.name)

    try:
        patcher = ManifestPatcher(path)
        patcher.set_google_ads_app_id("ca-app-pub-1111222233334444~5555666677")
        content = path.read_text()
        assert 'android:value="ca-app-pub-1111222233334444~5555666677"' in content
        assert "ca-app-pub-9249007709450981~3951571657" not in content
    finally:
        path.unlink(missing_ok=True)


def test_metadata_ad_patcher_replaces_units():
    fake_data = (
        b"PREFIX_"
        + MetadataAdPatcher.ORIGINAL_REWARDED
        + b"_MIDDLE_"
        + MetadataAdPatcher.ORIGINAL_INTERSTITIAL
        + b"_SUFFIX"
    )
    with tempfile.NamedTemporaryFile("wb+", suffix=".dat", delete=False) as f:
        f.write(fake_data)
        path = Path(f.name)

    try:
        patcher = MetadataAdPatcher(path)
        patched = patcher.patch(rewarded_id="my_custom_rew", interstitial_id="my_custom_int")
        assert patched is True
        content = path.read_bytes()
        assert b"my_custom_rew" in content
        assert b"my_custom_int" in content
        assert MetadataAdPatcher.ORIGINAL_REWARDED not in content
        assert MetadataAdPatcher.ORIGINAL_INTERSTITIAL not in content
    finally:
        path.unlink(missing_ok=True)


def test_manifest_patcher_overrides_non_debuggable_manifest(tmp_path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        '<manifest><application android:debuggable="false"></application></manifest>'
    )

    ManifestPatcher(manifest).enable_debugging()

    content = manifest.read_text()
    assert 'android:debuggable="true"' in content
    assert 'android:debuggable="false"' not in content


def test_apk_patcher_help_runs_in_isolated_python():
    script = Path(__file__).resolve().parents[2] / "scripts" / "patch_apk.py"

    result = subprocess.run(
        [sys.executable, "-I", str(script), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "Beatstar APK & Split Patcher" in result.stdout


def create_base_patcher(tmp_path, host):
    return BaseApkPatcher(
        apk_path=tmp_path / "base.apk",
        output_apk=tmp_path / "output" / "patched.apk",
        tools_dir=tmp_path / "tools",
        patch_dir=tmp_path / "patches",
        host=host,
        signer=object(),
    )


def test_base_apk_patcher_rejects_missing_metadata(tmp_path):
    patcher = create_base_patcher(tmp_path, "192.168.1.68")
    patcher.work_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="global-metadata.dat"):
        patcher._patch_metadata()


def test_base_apk_patcher_rejects_unpatched_gateway_host(tmp_path):
    patcher = create_base_patcher(tmp_path, "192.168.1.68")
    metadata = (
        patcher.work_dir
        / "assets"
        / "bin"
        / "Data"
        / "Managed"
        / "Metadata"
        / "global-metadata.dat"
    )
    metadata.parent.mkdir(parents=True)
    metadata.write_bytes(b"metadata without gateway string")

    with pytest.raises(ValueError, match="Gateway host"):
        patcher._patch_metadata()
