"""Tests for household load and grid status derivation."""

from custom_components.fronius_modbus.derived import LoadEstimator, grid_status


def test_grid_status_from_both_frequencies():
    """Combine inverter and meter frequency into a grid status."""
    assert grid_status(50.0, 49.99) == "On grid operating"
    assert grid_status(50.0, 0.0) == "Off grid operating"
    assert grid_status(0.0, 50.0) == "On grid"
    assert grid_status(0.0, 0.0) == "Off grid"
    assert grid_status(None, 50.0) is None


def _update(estimator, **overrides):
    values = {
        "meter_power_w": -2000.0,
        "inverter_power_w": 3000.0,
        "meter_location": 0,
        "pv_power_w": 3100.0,
        "storage_charge_power_w": 0.0,
        "storage_present": True,
    }
    values.update(overrides)
    return estimator.update(**values)


def test_load_at_the_feed_in_point_is_meter_plus_inverter():
    """At a feed-in meter, load is meter power plus inverter power."""
    assert _update(LoadEstimator()) == 1000.0


def test_load_needs_a_meter_location():
    """Without a known meter location, load cannot be derived."""
    assert _update(LoadEstimator(), meter_location=None) is None


def test_a_consumption_meter_reports_its_own_power():
    """A consumption-location meter reports load directly."""
    assert _update(LoadEstimator(), meter_location=1, meter_power_w=-450.0) == 450.0


def test_an_inverter_glitch_keeps_the_last_good_value_once():
    """A single-poll inverter glitch reuses the last good load, then goes unavailable."""
    estimator = LoadEstimator()
    assert _update(estimator) == 1000.0
    assert _update(estimator, inverter_power_w=0.0) == 1000.0
    assert _update(estimator, inverter_power_w=0.0) is None


def test_strong_charging_makes_a_negative_load_unavailable():
    """Heavy battery charging that would yield a negative load is unavailable instead."""
    assert (
        _update(
            LoadEstimator(),
            meter_power_w=-5000.0,
            inverter_power_w=3000.0,
            storage_charge_power_w=2500.0,
        )
        is None
    )
