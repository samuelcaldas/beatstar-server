import pytest
from server.commerce import (
    CommerceFeatureDisabledError,
    CommerceFeatureFlagManager,
    CommerceService,
    CurrencyType,
    InsufficientFundsError,
    ProductType,
    StoreCatalog,
    WalletManager,
)
from server.models.player import PlayerProfile


def test_commerce_feature_flags_toggle_and_assert():
    mgr = CommerceFeatureFlagManager()
    mgr.set_flag("iap_enabled", False)
    assert mgr.is_type_enabled(ProductType.GEMS) is False
    with pytest.raises(CommerceFeatureDisabledError):
        mgr.assert_enabled(ProductType.GEMS)

    mgr.set_flag("iap_enabled", True)
    assert mgr.is_type_enabled(ProductType.GEMS) is True
    mgr.assert_enabled(ProductType.GEMS)


def test_commerce_to_game_config_flags():
    mgr = CommerceFeatureFlagManager()
    flags = mgr.to_game_config_flags()
    assert "CanPurchaseMoreGemsFromContinue" in flags
    assert "ThemedBoxesEnabled" in flags
    assert "SeasonsEnabled" in flags
    assert "TrackSkinsEnabled" in flags


def test_store_catalog_lookup():
    catalog = StoreCatalog()
    item = catalog.get("box_rock")
    assert item is not None
    assert item.product_type == ProductType.THEMED_BOX
    assert item.cost == 149


def test_wallet_manager_deduct_and_credit():
    wallet = WalletManager()
    profile = PlayerProfile(coins=1000, gems=100)

    wallet.credit(profile, CurrencyType.GEMS, 50)
    assert profile.gems == 150

    wallet.deduct(profile, CurrencyType.GEMS, 50)
    assert profile.gems == 100

    with pytest.raises(InsufficientFundsError):
        wallet.deduct(profile, CurrencyType.GEMS, 500)


def test_commerce_service_purchase_flow():
    mgr = CommerceFeatureFlagManager()
    mgr.set_flag("shop_enabled", True)
    service = CommerceService(flags=mgr)
    profile = PlayerProfile(coins=1000, gems=100)

    # Compra 500 moedas por 25 gemas
    result = service.purchase(profile, "coins_500")
    assert result.success is True
    assert profile.gems == 75
    assert profile.coins == 1500


def test_commerce_service_purchase_blocked_when_flag_disabled():
    mgr = CommerceFeatureFlagManager()
    mgr.set_flag("lootboxes_enabled", False)
    service = CommerceService(flags=mgr)
    profile = PlayerProfile(coins=1000, gems=500)

    with pytest.raises(CommerceFeatureDisabledError):
        service.purchase(profile, "box_rock")


def test_commerce_service_tour_pass_buy_level():
    mgr = CommerceFeatureFlagManager()
    mgr.set_flag("premium_pass_enabled", True)
    service = CommerceService(flags=mgr)
    profile = PlayerProfile(coins=1000, gems=100)

    result = service.buy_season_level(profile, num_levels=2)
    assert result.success is True
    assert profile.gems == 40  # 100 - (2 * 30) = 40
    assert profile.customisation.get("tour_pass_level") == 3
