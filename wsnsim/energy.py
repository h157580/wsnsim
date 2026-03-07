from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict

class RadioState(Enum):
    """Possible hardware states of the radio."""
    SLEEP = auto()
    IDLE = auto()
    RX = auto()
    TX = auto()

@dataclass(frozen=True)
class RadioEnergyConfig:
    """Hardware specific energy parameters (mW and mJ)."""
    power_tx_mw: float
    power_rx_mw: float
    power_idle_mw: float
    power_sleep_mw: float
    
    # State transition overhead: How much energy (mJ) is needed to wake up from SLEEP?
    wakeup_cost_mj: float 
    
    # Battery capacity in Joules
    battery_capacity_joules: float

@dataclass
class EnergyMetrics:
    """Stores the current energy state and statistics of the node."""
    current_state: RadioState
    last_state_change_time: float
    total_energy_consumed_j: float
    wakeup_count: int
    
    # Time tracking for Duty Cycle calculation
    time_in_states: Dict[RadioState, float]

class EnergyModel:
    """Manages the energy state machine and consumption calculations for a node."""

    def __init__(
        self, 
        config: RadioEnergyConfig, 
        initial_state: RadioState,
        start_time: float = 0.0
    ):
        """Initializes the energy model.

        Args:
            config: Hardware specific energy parameters.
            initial_state: The starting state of the radio.
            start_time: The simulation time when this model starts.
        """
        self.config = config
        self.metrics = EnergyMetrics(
            current_state=initial_state,
            last_state_change_time=start_time,
            total_energy_consumed_j=0.0,
            wakeup_count=0,
            time_in_states={state: 0.0 for state in RadioState}
        )
        self._power_map = {
            RadioState.SLEEP: self.config.power_sleep_mw,
            RadioState.IDLE: self.config.power_idle_mw,
            RadioState.RX: self.config.power_rx_mw,
            RadioState.TX: self.config.power_tx_mw,
        }

    def update_state(self, new_state: RadioState, current_time: float) -> None:
        """Transitions to a new radio state and updates energy consumption.

        Args:
            new_state: The state to transition to.
            current_time: The current simulation time in seconds.

        Raises:
            ValueError: If current_time is less than the last state change time.
        """
        if current_time < self.metrics.last_state_change_time:
            raise ValueError("Time cannot move backwards.")
            
        if new_state == self.metrics.current_state:
            return

        # If already dead, stay in SLEEP and update time (if not already there)
        if self.metrics.total_energy_consumed_j >= self.config.battery_capacity_joules:
            self.metrics.current_state = RadioState.SLEEP
            self.metrics.last_state_change_time = current_time
            return

        delta_t = current_time - self.metrics.last_state_change_time
        power_mw = self._power_map[self.metrics.current_state]
        energy_j = (power_mw * delta_t) / 1000.0
        
        # Check if we run out of energy during the previous state duration
        remaining_j = self.config.battery_capacity_joules - self.metrics.total_energy_consumed_j
        
        if energy_j >= remaining_j:
            # Node died during this interval
            # Time until death = (Remaining Energy (J) * 1000) / Power (mW)
            # If power is 0 (SLEEP), this branch shouldn't be hit as energy_j would be 0
            # unless remaining_j is also 0, which is handled by the "already dead" check.
            t_alive = (remaining_j * 1000.0) / power_mw if power_mw > 0 else delta_t
            
            self.metrics.time_in_states[self.metrics.current_state] += t_alive
            self.metrics.total_energy_consumed_j = self.config.battery_capacity_joules
            self.metrics.current_state = RadioState.SLEEP
            self.metrics.last_state_change_time = self.metrics.last_state_change_time + t_alive
            return

        # Update energy and time for the previous state
        self.metrics.total_energy_consumed_j += energy_j
        self.metrics.time_in_states[self.metrics.current_state] += delta_t
        self.metrics.last_state_change_time = current_time

        # Handle wakeup transition cost (from SLEEP to active)
        if self.metrics.current_state == RadioState.SLEEP and new_state != RadioState.SLEEP:
            wakeup_j = self.config.wakeup_cost_mj / 1000.0
            
            if self.metrics.total_energy_consumed_j + wakeup_j >= self.config.battery_capacity_joules:
                self.metrics.total_energy_consumed_j = self.config.battery_capacity_joules
                self.metrics.current_state = RadioState.SLEEP
                return
            
            self.metrics.total_energy_consumed_j += wakeup_j
            self.metrics.wakeup_count += 1

        self.metrics.current_state = new_state

    def get_total_consumed_j(self, current_time: float) -> float:
        """Calculates total consumption up to current_time without changing state.

        Args:
            current_time: The current simulation time in seconds.

        Returns:
            Total energy consumed in Joules, capped at battery capacity.
        """
        if current_time < self.metrics.last_state_change_time:
            return self.metrics.total_energy_consumed_j
            
        delta_t = current_time - self.metrics.last_state_change_time
        power_mw = self._power_map[self.metrics.current_state]
        energy_j = (power_mw * delta_t) / 1000.0
        
        total = self.metrics.total_energy_consumed_j + energy_j
        return min(total, self.config.battery_capacity_joules)

    def get_remaining_energy_j(self, current_time: float) -> float:
        """Returns the remaining battery energy in Joules at the given time.

        Args:
            current_time: The current simulation time in seconds.
        """
        consumed = self.get_total_consumed_j(current_time)
        return max(0.0, self.config.battery_capacity_joules - consumed)

    def is_out_of_energy(self, current_time: float) -> bool:
        """Checks if the battery is exhausted at the given time."""
        return self.get_remaining_energy_j(current_time) <= 0.0
