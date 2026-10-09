import tempfile
from pathlib import Path
import pytest
from scripts.patch_apk import ManifestPatcher
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
