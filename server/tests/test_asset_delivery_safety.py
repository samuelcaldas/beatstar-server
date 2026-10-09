"""Asset delivery regressions using disposable synthetic data only."""
import hashlib
import pytest
from httpx import ASGITransport, AsyncClient
from server.app import app
from server.handlers.cms_handler import CMSHandler
from server.models.headers import ClientHeader


@pytest.fixture
async def asset_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/bundles").mkdir(parents=True)
    (tmp_path / "data/configs").mkdir()
    (tmp_path / "data/bundles/example.bundle").write_bytes(b"0123456789")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.parametrize("range_header, status, expected", [
    ("bytes=-5", 206, b"56789"), ("bytes=3-", 206, b"3456789"),
    ("bytes=100-", 416, None), ("bytes=8-3", 400, None),
    ("bytes=abc", 400, None),
])
async def test_bundle_ranges(asset_client, range_header, status, expected):
    response = await asset_client.get("/assets/bundles/example.bundle", headers={"Range": range_header})
    assert response.status_code == status
    if expected is not None:
        assert response.content == expected


async def test_missing_binary_config_is_not_successful_json(asset_client):
    response = await asset_client.get("/assets/configs/SongConfig.bin")
    assert response.status_code == 404


async def test_symlinked_bundle_is_not_public(asset_client, tmp_path):
    secret = tmp_path / "private"
    secret.write_bytes(b"not-public")
    (tmp_path / "data/bundles/secret.bundle").symlink_to(secret)
    response = await asset_client.get("/assets/bundles/secret.bundle")
    assert response.status_code == 404


async def test_cms_advertises_fetchable_binary_with_real_digest(asset_client, tmp_path):
    payload = b"\x08\x96\x01"
    (tmp_path / "data/configs/SongConfig.bin").write_bytes(payload)
    response = await CMSHandler().handle(ClientHeader(service="cmsservice"), {})
    resources = response["blah"]["blah"]["blah"]
    entry = next(item for item in resources if item["name"] == "SongConfig")
    result = await asset_client.get(entry["url"])
    assert result.content == payload
    assert result.headers["content-type"] == "application/octet-stream"
    assert entry["hash"] == hashlib.sha256(payload).hexdigest()
    assert not any(item["name"] == "BeatmapsConfig" for item in resources)
