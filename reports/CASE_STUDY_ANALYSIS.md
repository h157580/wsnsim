# Case Study Analysis: Forest Fire Detection

This document details the energy model and the logic used to determine the optimal design point for the Forest Fire Detection scenario.

## 1. Energy Model Definition

The energy consumption ($E$) is modeled in **Joules (J)**, representing the integrated power consumption over a standard operational period (1 hour).

### The Formula
$$E = (P_{tx} \times \eta + P_{base}) \times DC$$

Where:
- **$P_{tx}$ (TX Power)**: The transmit power in milliwatts (mW). We sweep this from **1 mW to 20 mW** to cover low-power short-range and high-power long-range communication.
- **$\eta$ (Efficiency Factor = 0.5)**: Represents the Power Amplifier (PA) efficiency. In typical WSN radios (e.g., CC2420), generating 20mW of RF power often requires ~40mW of electrical power.
- **$P_{base}$ (Base Consumption = 5.0 mW)**: The constant power draw of the microcontroller (MCU) and the radio in RX/Idle mode. This value is derived from typical low-power sensor nodes (e.g., TI MSP430 + CC series) where idle/listening consumes ~3-7 mW.
- **$DC$ (Duty Cycle)**: The fraction of time the node is active. Swept from **1% (0.01) to 30% (0.30)**.

## 2. Parameter Derivation Logic

The values were selected to reflect realistic constraints of a forest deployment:

| Parameter | Value / Range | Rational / Source |
| :--- | :--- | :--- |
| **TX Power** | 1 - 20 mW | Based on IEEE 802.15.4 (Zigbee) standards for outdoor sensors. |
| **Base Power** | 5.0 mW | Average of MCU active sleep (1mW) + Radio RX/Listen (4mW). |
| **Efficiency** | 0.5 | Conservative estimate for Class AB power amplifiers in standard RF transceivers. |
| **Duty Cycle** | 1% - 30% | Balances the "Always On" safety requirement vs. the "Years on Battery" goal. |

## 3. The Optimal Design Point Discovery

The "Optimal" point was identified using a **constrained Pareto-optimal search**:

1. **Exploration**: 4,000 simulations (400 configurations $\times$ 10 repetitions) were executed to map the trade-off space.
2. **Hard Constraints (Safety-First)**: 
   - **Reliability (PDR) > 90%**: An alert must reach the sink with high probability.
   - **Latency < 60s**: The detection must be reported within one minute of ignition.
3. **Pareto Selection**: From all points meeting the safety constraints, the one with the **minimum Energy ($E$)** was selected.

### Selected Configuration:
- **TX Power**: 11.00 mW
- **Duty Cycle**: 16.3%
- **Resulting Energy**: ~1.71 Joules/period
- **Resulting Reliability**: 90.5% PDR
- **Resulting Latency**: 55.5 seconds

## 4. Hardware Configuration Recommendations

To achieve the performance and battery life indicated by this optimal design point, the following hardware stack is recommended:

### Power Source: Li-SOCl2 Battery
- **Type**: 3.6V Lithium Thionyl Chloride (e.g., **Saft LS14500** AA-size).
- **Capacity**: ~2600 mAh (approx. 33,000 Joules).
- **Estimated Lifetime**: ~1.8 - 2.0 years in forest conditions, accounting for self-discharge and 16.3% duty cycle.
- **Why**: Excellent stability in extreme temperatures (-60°C to +85°C), crucial for forest environments.

### Core Processing & Radio: SoC (System-on-Chip)
- **Recommendation**: **Nordic nRF52840** or **TI CC2652R**.
- **Radio Protocol**: IEEE 802.15.4 (Zigbee/Thread compatible).
- **Capability**: Both support the required 11mW (approx +10dBm) TX power and have ultra-low-power sleep modes (< 2µA) to keep $P_{base}$ at or below the modeled 5.0 mW average.

### Sensors: Low-Power Environmental Suite
- **Recommendation**: **Bosch BME680** (Gas, Pressure, Temperature, Humidity).
- **Strategy**: Use the Edge AI logic (EWMA/Z-Score) on the MCU to only wake the radio when the sensor detects a rapid temperature spike or gas concentration change.

### Antenna: High-Gain Dipole
- **Type**: 2.1 dBi Omnidirectional dipole with IP67 housing.
- **Why**: Forest foliage causes significant signal attenuation (shadowing). A high-gain antenna compensates for the 11mW limit while maintaining the 90%+ PDR goal.

