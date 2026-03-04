from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.random import Generator

@dataclass(frozen=True)
class ChannelConfig:
    """Configuration for the radio channel model.
    
    All power values are in milliWatts (mW) to follow project standards.
    """
    d0: float = 1.0                # Reference distance (m)
    pl_d0: float = 40.0            # Path loss at reference distance (dB)
    n: float = 3.0                 # Path loss exponent
    sigma: float = 4.0             # Shadowing standard deviation (dB)
    # -105 dBm is approx 3.16e-11 mW
    noise_floor_mw: float = 10**(-105.0 / 10.0) 
    packet_length: int = 1024       # Packet length in bits

class ChannelModel:
    """Implements radio propagation models using mW for power."""
    
    def __init__(self, config: ChannelConfig, rng: Generator) -> None:
        self.config = config
        self.rng = rng

    def get_path_loss(self, distance: float) -> float:
        """Calculate log-distance path loss in dB."""
        if distance <= self.config.d0:
            return self.config.pl_d0
        
        return self.config.pl_d0 + 10 * self.config.n * np.log10(distance / self.config.d0)

    def get_shadowing(self) -> float:
        """Calculate log-normal shadowing in dB."""
        return float(self.rng.normal(0, self.config.sigma))

    def calculate_prr(self, tx_power_mw: float, distance: float, use_shadowing: bool = True) -> float:
        """Calculate Packet Reception Rate (PRR).
        
        Args:
            tx_power_mw: Transmit power in milliWatts (mW).
            distance: Distance in meters (m).
            use_shadowing: Whether to include random shadowing.
        """
        if tx_power_mw <= 0:
            raise ValueError("TX power must be positive.")

        # Convert TX power mW -> dBm for link budget
        tx_power_dbm = 10 * np.log10(tx_power_mw)
        
        # Calculate Path Loss
        pl = self.get_path_loss(distance)
        if use_shadowing:
            pl += self.get_shadowing()
        
        # RX Power (dBm) = TX Power (dBm) - Path Loss (dB)
        rx_power_dbm = tx_power_dbm - pl
        
        # Convert noise floor mW -> dBm
        noise_floor_dbm = 10 * np.log10(self.config.noise_floor_mw)
        
        # SNR (dB) = RX Power (dBm) - Noise Floor (dBm)
        snr_db = rx_power_dbm - noise_floor_dbm
        snr_linear = 10**(snr_db / 10.0)
        
        # BER for non-coherent FSK
        ber = 0.5 * np.exp(-0.5 * snr_linear)
        ber = np.clip(ber, 0, 0.5)
        
        # PRR = (1 - BER)^L
        prr = (1 - ber)**self.config.packet_length
        return float(prr)

    def is_received(self, tx_power_mw: float, distance: float) -> bool:
        """Stochastically determine if a packet is received."""
        prr = self.calculate_prr(tx_power_mw, distance, use_shadowing=True)
        return self.rng.random() < prr
