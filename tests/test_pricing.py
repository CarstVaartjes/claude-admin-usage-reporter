from app.pricing import PRICING, estimate_cost_usd, load_pricing


def test_load_pricing_no_overrides(tmp_path):
    pricing = load_pricing(tmp_path / "does_not_exist.yaml")
    assert pricing == PRICING


def test_load_pricing_with_overrides(tmp_path):
    overrides_path = tmp_path / "pricing_overrides.yaml"
    overrides_path.write_text("claude-sonnet-4-6:\n  input: 999.0\n")
    pricing = load_pricing(overrides_path)
    assert pricing["claude-sonnet-4-6"]["input"] == 999.0
    # untouched rate for the same model stays as default
    assert pricing["claude-sonnet-4-6"]["output"] == PRICING["claude-sonnet-4-6"]["output"]


def test_estimate_cost_usd_uses_default_for_unknown_model():
    row = {"model": "some-future-model", "uncached_input_tokens": 1_000_000, "output_tokens": 0}
    pricing = load_pricing(None)
    cost = estimate_cost_usd(row, pricing)
    assert cost == pricing["_default"]["input"]


def test_estimate_cost_usd_includes_cache_tokens():
    row = {
        "model": "claude-sonnet-4-6",
        "uncached_input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 1_000_000,
        "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 1_000_000},
    }
    pricing = load_pricing(None)
    cost = estimate_cost_usd(row, pricing)
    rates = pricing["claude-sonnet-4-6"]
    expected = rates["cache_read"] + rates["cache_write_5m"] + rates["cache_write_1h"]
    assert round(cost, 6) == round(expected, 6)
