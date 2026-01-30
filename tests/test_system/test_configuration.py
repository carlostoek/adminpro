"""
Configuration Management Tests.

Tests for configuration validation, setters, and defaults:
- Configuration validation (fully configured vs missing items)
- Configuration setters with validation
- Configuration summary generation
- Configuration reset to defaults
"""
import pytest


async def test_config_validation_fully_configured(container):
    """Verify configuration status detection when fully configured."""
    # Set all required config values via direct config access
    await container.config.set_wait_time(5)
    config = await container.config.get_config()
    config.vip_channel_id = "-1001234567890"
    config.free_channel_id = "-1000987654321"
    await container.config.session.commit()

    # Check configuration status
    status = await container.config.get_config_status()

    assert status["is_configured"] is True
    assert len(status.get("missing", [])) == 0


async def test_config_validation_missing_items(container):
    """Verify missing configuration detection."""
    # Reset to defaults (clears channel IDs)
    await container.config.reset_to_defaults()

    # Check configuration status
    status = await container.config.get_config_status()

    assert status["is_configured"] is False
    assert "Canal VIP" in status.get("missing", []) or "Canal Free" in status.get("missing", [])


async def test_config_is_fully_configured(container):
    """Verify is_fully_configured method works correctly."""
    # Initially should be configured (from fixture defaults)
    is_configured = await container.config.is_fully_configured()
    assert is_configured is True

    # Reset to defaults (clears channel IDs)
    await container.config.reset_to_defaults()

    # Now should not be configured
    is_configured = await container.config.is_fully_configured()
    assert is_configured is False


async def test_config_setters_validation_wait_time(container):
    """Verify set_wait_time validates input correctly."""
    # Valid values should work
    await container.config.set_wait_time(1)
    await container.config.set_wait_time(60)
    await container.config.set_wait_time(1440)  # 24 hours

    # Invalid values should raise ValueError
    with pytest.raises(ValueError, match="al menos 1 minuto"):
        await container.config.set_wait_time(0)

    with pytest.raises(ValueError, match="al menos 1 minuto"):
        await container.config.set_wait_time(-5)

    with pytest.raises(ValueError, match="al menos 1 minuto"):
        await container.config.set_wait_time(-1)


async def test_config_setters_validation_vip_reactions(container):
    """Verify set_vip_reactions validates input correctly."""
    # Valid values should work
    await container.config.set_vip_reactions(["👍"])
    await container.config.set_vip_reactions(["👍", "❤️", "🔥"])
    await container.config.set_vip_reactions(["👍"] * 10)  # Max 10

    # Empty list should raise ValueError
    with pytest.raises(ValueError, match="al menos 1 reacción"):
        await container.config.set_vip_reactions([])

    # More than 10 should raise ValueError
    with pytest.raises(ValueError, match="Máximo 10 reacciones"):
        await container.config.set_vip_reactions(["👍"] * 11)


async def test_config_setters_validation_free_reactions(container):
    """Verify set_free_reactions validates input correctly."""
    # Valid values should work
    await container.config.set_free_reactions(["👍"])
    await container.config.set_free_reactions(["👍", "🙏"])
    await container.config.set_free_reactions(["👍"] * 10)

    # Empty list should raise ValueError
    with pytest.raises(ValueError, match="al menos 1 reacción"):
        await container.config.set_free_reactions([])

    # More than 10 should raise ValueError
    with pytest.raises(ValueError, match="Máximo 10 reacciones"):
        await container.config.set_free_reactions(["👍"] * 11)


async def test_config_setters_validation_subscription_fees(container):
    """Verify set_subscription_fees validates input correctly."""
    # Valid values should work
    await container.config.set_subscription_fees({"monthly": 10.0})
    await container.config.set_subscription_fees({"monthly": 10.0, "yearly": 100.0})
    await container.config.set_subscription_fees({"monthly": 0.0})  # Zero is valid

    # Empty dict should raise ValueError
    with pytest.raises(ValueError, match="al menos 1 tarifa"):
        await container.config.set_subscription_fees({})

    # Negative values should raise ValueError
    with pytest.raises(ValueError, match="no puede ser negativa"):
        await container.config.set_subscription_fees({"monthly": -10.0})

    with pytest.raises(ValueError, match="no puede ser negativa"):
        await container.config.set_subscription_fees({
            "monthly": 10.0,
            "yearly": -100.0
        })


async def test_config_setters_validation_social_media(container):
    """Verify social media setters validate input correctly."""
    # Valid values should work
    await container.config.set_social_instagram("@diana")
    await container.config.set_social_tiktok("@diana_tiktok")
    await container.config.set_social_x("@diana_x")

    # Empty strings should raise ValueError
    with pytest.raises(ValueError, match="cannot be empty"):
        await container.config.set_social_instagram("")

    with pytest.raises(ValueError, match="cannot be empty"):
        await container.config.set_social_tiktok("   ")  # Whitespace only

    with pytest.raises(ValueError, match="cannot be empty"):
        await container.config.set_social_x("")


async def test_config_setters_validation_invite_link(container):
    """Verify invite link setter validates input correctly."""
    # Valid value should work
    await container.config.set_free_channel_invite_link("https://t.me/+TestLink123")

    # Empty strings should raise ValueError
    with pytest.raises(ValueError, match="cannot be empty"):
        await container.config.set_free_channel_invite_link("")

    with pytest.raises(ValueError, match="cannot be empty"):
        await container.config.set_free_channel_invite_link("   ")


async def test_config_summary_generation(container):
    """Verify configuration summary for admin panel."""
    # Set some config values via direct config access
    await container.config.set_wait_time(10)
    config = await container.config.get_config()
    config.vip_channel_id = "-1001234567890"
    config.free_channel_id = "-1000987654321"
    await container.config.session.commit()

    # Get summary
    summary = await container.config.get_config_summary()

    assert summary is not None
    assert isinstance(summary, str)
    assert "Estado de Configuración" in summary
    assert "Canal VIP" in summary
    assert "Canal Free" in summary
    assert "-1001234567890" in summary
    assert "-1000987654321" in summary
    assert "10" in summary  # wait_time


async def test_config_summary_shows_missing(container):
    """Verify configuration summary shows missing items when not configured."""
    # Reset to defaults (clears channel IDs)
    await container.config.reset_to_defaults()

    # Get summary
    summary = await container.config.get_config_summary()

    # Should indicate missing configuration
    assert "Faltante" in summary or "No configurado" in summary


async def test_config_reset_to_defaults(container):
    """Verify configuration can be reset to defaults."""
    # Modify config
    await container.config.set_wait_time(999)
    await container.config.set_vip_reactions(["🔥"])
    await container.config.set_free_reactions(["👎"])

    # Reset to defaults
    await container.config.reset_to_defaults()

    # Verify reset
    config = await container.config.get_config()
    assert config.wait_time_minutes != 999  # Should be default value
    assert config.vip_channel_id is None
    assert config.free_channel_id is None


async def test_config_getters_return_correct_types(container):
    """Verify all config getters return expected types."""
    # Set test values via direct config access
    await container.config.set_wait_time(15)
    await container.config.set_vip_reactions(["👍", "❤️"])
    await container.config.set_free_reactions(["👍"])
    await container.config.set_subscription_fees({"monthly": 15.0})
    await container.config.set_social_instagram("@test")
    await container.config.set_social_tiktok("@test_tiktok")
    await container.config.set_social_x("@test_x")
    await container.config.set_free_channel_invite_link("https://t.me/+Test123")

    # Set channel IDs via direct config access
    config = await container.config.get_config()
    config.vip_channel_id = "-1001111111111"
    config.free_channel_id = "-1002222222222"
    await container.config.session.commit()

    # Test getters return correct types
    wait_time = await container.config.get_wait_time()
    assert isinstance(wait_time, int)
    assert wait_time == 15

    vip_channel = await container.config.get_vip_channel_id()
    assert isinstance(vip_channel, str)
    assert vip_channel == "-1001111111111"

    free_channel = await container.config.get_free_channel_id()
    assert isinstance(free_channel, str)
    assert free_channel == "-1002222222222"

    vip_reactions = await container.config.get_vip_reactions()
    assert isinstance(vip_reactions, list)
    assert vip_reactions == ["👍", "❤️"]

    free_reactions = await container.config.get_free_reactions()
    assert isinstance(free_reactions, list)
    assert free_reactions == ["👍"]

    fees = await container.config.get_subscription_fees()
    assert isinstance(fees, dict)
    assert fees == {"monthly": 15.0}

    instagram = await container.config.get_social_instagram()
    assert isinstance(instagram, str)
    assert instagram == "@test"

    tiktok = await container.config.get_social_tiktok()
    assert isinstance(tiktok, str)
    assert tiktok == "@test_tiktok"

    x = await container.config.get_social_x()
    assert isinstance(x, str)
    assert x == "@test_x"

    invite_link = await container.config.get_free_channel_invite_link()
    assert isinstance(invite_link, str)
    assert invite_link == "https://t.me/+Test123"


async def test_config_getters_return_none_when_not_set(container):
    """Verify getters return None for unset optional values."""
    # Reset to defaults (clears optional values)
    await container.config.reset_to_defaults()

    vip_channel = await container.config.get_vip_channel_id()
    assert vip_channel is None

    free_channel = await container.config.get_free_channel_id()
    assert free_channel is None

    instagram = await container.config.get_social_instagram()
    assert instagram is None

    tiktok = await container.config.get_social_tiktok()
    assert tiktok is None

    x = await container.config.get_social_x()
    assert x is None

    invite_link = await container.config.get_free_channel_invite_link()
    assert invite_link is None


async def test_config_get_social_media_links(container):
    """Verify get_social_media_links returns dict of configured platforms."""
    # Reset first
    await container.config.reset_to_defaults()

    # Empty when nothing configured
    links = await container.config.get_social_media_links()
    assert links == {}

    # Set some social media
    await container.config.set_social_instagram("@diana")
    await container.config.set_social_tiktok("@diana_tiktok")
    # Don't set X

    links = await container.config.get_social_media_links()
    assert "instagram" in links
    assert "tiktok" in links
    assert "x" not in links
    assert links["instagram"] == "@diana"
    assert links["tiktok"] == "@diana_tiktok"


async def test_config_status_returns_all_fields(container):
    """Verify get_config_status returns all expected fields."""
    status = await container.config.get_config_status()

    assert "is_configured" in status
    assert "vip_channel_id" in status
    assert "free_channel_id" in status
    assert "wait_time_minutes" in status
    assert "vip_reactions_count" in status
    assert "free_reactions_count" in status
    assert "missing" in status

    assert isinstance(status["is_configured"], bool)
    assert isinstance(status["wait_time_minutes"], int)
    assert isinstance(status["vip_reactions_count"], int)
    assert isinstance(status["free_reactions_count"], int)
    assert isinstance(status["missing"], list)
