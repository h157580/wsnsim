from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING
from .common import Packet

if TYPE_CHECKING:
    from .energy import EnergyModel

@dataclass(frozen=True)
class SecurityConfig:
    """Security overhead parameters.
    
    Default values are generic; can be configured to match specific algorithms.
    """
    # Energy cost in Joules per packet (CPU processing)
    crypto_energy_j: float = 0.000005  
    
    # Latency added by crypto processing in seconds
    crypto_latency_s: float = 0.0005   
    
    # Extra bytes added to the packet (Auth Tag, Nonce, IV, Padding)
    overhead_bytes: int = 28

class SecurityModel:
    """Handles security metadata (nonces) and calculates overhead costs."""
    
    def __init__(self, node_id: int, config: SecurityConfig = SecurityConfig()):
        self.node_id = node_id
        self.config = config
        
        # Next nonce to use for outgoing packets
        self.next_outgoing_nonce = 1
        
        # Last seen nonce for each neighbor to prevent replay attacks
        self.last_incoming_nonces: Dict[int, int] = {}

    def sign_packet(self, packet: Packet, energy_model: Optional[EnergyModel] = None, current_time: float = 0.0) -> float:
        """Apply security overhead for an outgoing packet.
        
        Returns:
            Latency added by crypto processing. Returns 0 if node is dead.
        """
        # Apply energy cost directly to the energy model if provided
        if energy_model:
            is_alive = energy_model.consume_energy(self.config.crypto_energy_j, current_time)
            if not is_alive:
                return 0.0 # Cannot sign if dead
                
        packet.nonce = self.next_outgoing_nonce
        self.next_outgoing_nonce += 1
        
        # Add physical size overhead
        packet.size_bytes += self.config.overhead_bytes
                
        return self.config.crypto_latency_s

    def verify_packet(self, packet: Packet, energy_model: Optional[EnergyModel] = None, current_time: float = 0.0) -> bool:
        """Verify an incoming packet and apply security overhead.
        
        Returns:
            True if packet is valid AND node is alive, False otherwise.
        """
        # Apply energy cost for verification attempt
        if energy_model:
            is_alive = energy_model.consume_energy(self.config.crypto_energy_j, current_time)
            if not is_alive:
                return False

        # Check for replay attack
        last_nonce = self.last_incoming_nonces.get(packet.src, 0)
        
        if packet.nonce > last_nonce:
            self.last_incoming_nonces[packet.src] = packet.nonce
            return True
        else:
            print(f"DEBUG: Node {self.node_id} REJECTED replay from {packet.src}: payload={packet.payload}, nonce={packet.nonce} <= last {last_nonce}")
            return False
