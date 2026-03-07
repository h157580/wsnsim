import numpy as np
import matplotlib.pyplot as plt
from wsnsim.energy import RadioEnergyConfig, RadioState

def calculate_lifetime_days(duty_cycle_percent: float, config: RadioEnergyConfig) -> float:
    """Calculates the estimated lifetime in days for a given duty cycle.
    
    Assumes duty cycle is spent in IDLE (listening) and the rest in SLEEP.
    Transition costs and TX/RX specifics are ignored for this simplified estimate.
    """
    dc = duty_cycle_percent / 100.0
    
    # Average power in mW
    avg_power_mw = (dc * config.power_idle_mw) + ((1.0 - dc) * config.power_sleep_mw)
    
    # Lifetime in seconds = (Capacity in J * 1000) / Power in mW
    lifetime_s = (config.battery_capacity_joules * 1000.0) / avg_power_mw
    
    return lifetime_s / 86400.0 # Convert to days

def run_experiment():
    # Typical parameters (e.g., CC2420 radio + 2x AA batteries)
    # 2x AA batteries ~ 18000 Joules
    config = RadioEnergyConfig(
        power_tx_mw=52.2,    # 0 dBm
        power_rx_mw=56.4,    # Listening
        power_idle_mw=56.4,  # Same as RX for many radios
        power_sleep_mw=0.06, # 20 uA @ 3V
        wakeup_cost_mj=0.0,
        battery_capacity_joules=18000.0 
    )

    # Duty cycles from 0.1% to 100% (log scale for better visualization at low DC)
    duty_cycles = np.logspace(-1, 2, num=100) # 0.1 to 100
    lifetimes = [calculate_lifetime_days(dc, config) for dc in duty_cycles]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(duty_cycles, lifetimes, linewidth=2, color='blue', label='CC2420 + 2xAA')
    
    # Log scale for X-axis since WSNs usually operate at < 1% DC
    plt.xscale('log')
    plt.yscale('log')
    
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.xlabel('Duty Cycle (%)', fontsize=12)
    plt.ylabel('Estimated Lifetime (Days)', fontsize=12)
    plt.title('Node Lifetime vs. Radio Duty Cycle', fontsize=14)
    
    # Add some key points
    key_dcs = [0.1, 1.0, 10.0, 100.0]
    for dc in key_dcs:
        life = calculate_lifetime_days(dc, config)
        plt.scatter(dc, life, color='red')
        plt.annotate(f"{life:.1f} days", (dc, life), textcoords="offset points", 
                     xytext=(0,10), ha='center', fontsize=9)

    plt.legend()
    
    output_path = "reports/figures/lifetime_vs_dutycycle.png"
    plt.savefig(output_path)
    print(f"Plot saved to {output_path}")

    # Also print a small table for the CLI
    print("\nDuty Cycle (%) | Est. Lifetime (Days) | Est. Lifetime (Years)")
    print("-" * 55)
    for dc in [0.1, 0.5, 1.0, 5.0, 10.0, 100.0]:
        life = calculate_lifetime_days(dc, config)
        print(f"{dc:14.1f} | {life:20.1f} | {life/365.25:21.2f}")

if __name__ == "__main__":
    run_experiment()
