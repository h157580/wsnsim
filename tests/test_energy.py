import pytest
from wsnsim.energy import RadioState, RadioEnergyConfig, EnergyModel

@pytest.fixture
def tiny_battery_config():
    """Config with a small 0.1 Joule battery for precise testing."""
    return RadioEnergyConfig(
        power_tx_mw=20.0,
        power_rx_mw=22.0,
        power_idle_mw=1.0,
        power_sleep_mw=0.1,
        wakeup_cost_mj=0.05,
        battery_capacity_joules=0.1 
    )

def test_energy_model_scenario(tiny_battery_config):
    """Formalized version of the manual simple test."""
    model = EnergyModel(config=tiny_battery_config, initial_state=RadioState.SLEEP, start_time=0.0)
    
    # 1. 10s Sleep -> RX
    # Sleep energy: (0.1 mW * 10s) / 1000 = 0.001 J
    # Wakeup cost: 0.05 mJ / 1000 = 0.00005 J
    model.update_state(RadioState.RX, current_time=10.0)
    assert pytest.approx(model.metrics.total_energy_consumed_j) == 0.00105
    assert model.metrics.wakeup_count == 1

    # 2. 0.1s RX -> TX
    # RX energy: (22 mW * 0.1s) / 1000 = 0.0022 J
    model.update_state(RadioState.TX, current_time=10.1)
    assert pytest.approx(model.metrics.total_energy_consumed_j) == 0.00105 + 0.0022

    # 3. 0.05s TX -> SLEEP
    # TX energy: (20 mW * 0.05s) / 1000 = 0.001 J
    model.update_state(RadioState.SLEEP, current_time=10.15)
    
    expected_total = 0.00105 + 0.0022 + 0.001
    assert pytest.approx(model.metrics.total_energy_consumed_j) == expected_total
    assert pytest.approx(model.get_remaining_energy_j(10.15)) == 0.1 - expected_total

    # Verify time in states
    assert pytest.approx(model.metrics.time_in_states[RadioState.SLEEP]) == 10.0
    assert pytest.approx(model.metrics.time_in_states[RadioState.RX]) == 0.1
    assert pytest.approx(model.metrics.time_in_states[RadioState.TX]) == 0.05

def test_battery_exhaustion_mid_interval():
    """Verify that the node 'dies' accurately mid-interval and records correct time."""
    config = RadioEnergyConfig(
        power_tx_mw=1000.0, # 1W = 1000 mJ/s
        power_rx_mw=0.0,
        power_idle_mw=0.0,
        power_sleep_mw=0.0,
        wakeup_cost_mj=0.0,
        battery_capacity_joules=1.0 # 1000 mJ
    )
    model = EnergyModel(config, RadioState.TX, start_time=0.0)
    
    # At 1W, 1 Joule lasts exactly 1.0 second.
    # We trigger an update at 2.0 seconds.
    model.update_state(RadioState.SLEEP, current_time=2.0)
    
    assert model.metrics.total_energy_consumed_j == 1.0
    assert model.metrics.current_state == RadioState.SLEEP
    # Crucial: it should record only the 1.0s it was alive in TX
    assert model.metrics.time_in_states[RadioState.TX] == 1.0
    assert model.metrics.last_state_change_time == 1.0
    assert model.is_out_of_energy(2.0)

def test_battery_exhaustion_exact_transition():
    """Verify that the node 'dies' exactly at the transition time when energy runs out."""
    config = RadioEnergyConfig(
        power_tx_mw=500.0, # 0.5W = 500 mJ/s
        power_rx_mw=0.0,
        power_idle_mw=0.0,
        power_sleep_mw=0.0,
        wakeup_cost_mj=0.0,
        battery_capacity_joules=1.0 # 1000 mJ
    )
    model = EnergyModel(config, RadioState.TX, start_time=0.0)
    
    # At 500 mW, 1 Joule lasts exactly 2.0 seconds.
    # We trigger an update at 2.0 seconds.
    model.update_state(RadioState.SLEEP, current_time=2.0)
    
    assert model.metrics.total_energy_consumed_j == 1.0
    assert model.metrics.current_state == RadioState.SLEEP
    assert model.metrics.time_in_states[RadioState.TX] == 2.0
    assert model.metrics.last_state_change_time == 2.0
    assert model.is_out_of_energy(2.0)


def test_battery_exhaustion_during_wakeup():
    """Verify that the node 'dies' during the wakeup cost if energy runs out."""
    config = RadioEnergyConfig(
        power_tx_mw=0.0,
        power_rx_mw=0.0,
        power_idle_mw=0.0,
        power_sleep_mw=0.0,
        wakeup_cost_mj=1000.0, # 1 Joule wakeup cost
        battery_capacity_joules=1.0 # 1 Joule total
    )
    model = EnergyModel(config, RadioState.SLEEP, start_time=0.0)
    
    # Attempt to wake up at time 1.0s, which should consume the entire battery.
    model.update_state(RadioState.RX, current_time=1.0)
    
    assert model.metrics.total_energy_consumed_j == 1.0
    assert model.metrics.current_state == RadioState.SLEEP # Should revert to SLEEP if dead
    assert model.is_out_of_energy(1.0)
    assert model.metrics.time_in_states[RadioState.SLEEP] == 1.0

def test_time_backwards_error(tiny_battery_config):
    model = EnergyModel(tiny_battery_config, RadioState.IDLE, start_time=10.0)
    with pytest.raises(ValueError, match="Time cannot move backwards"):
        model.update_state(RadioState.TX, current_time=5.0)

def test_energy_guards_and_sanity(tiny_battery_config):
    """Sanity check: time sum consistency and energy floor guard."""
    model = EnergyModel(tiny_battery_config, RadioState.TX, start_time=0.0)
    
    # 1. Energy floor: Try to consume more than available
    # TX is 20mW. 0.1J lasts 5s.
    # Check at 10s.
    assert model.get_remaining_energy_j(10.0) == 0.0
    assert model.get_total_consumed_j(10.0) == 0.1
    
    # 2. Time consistency: Update multiple times and check sum
    model = EnergyModel(tiny_battery_config, RadioState.IDLE, start_time=0.0)
    model.update_state(RadioState.RX, 1.0)
    model.update_state(RadioState.TX, 2.5)
    model.update_state(RadioState.SLEEP, 4.0)
    
    total_time_in_states = sum(model.metrics.time_in_states.values())
    assert pytest.approx(total_time_in_states) == 4.0
    
    # 3. Consumption monotonicity
    consumed_before = model.metrics.total_energy_consumed_j
    model.update_state(RadioState.IDLE, 5.0)
    assert model.metrics.total_energy_consumed_j >= consumed_before
