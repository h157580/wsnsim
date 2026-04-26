# REPORT: In-Network Data Aggregation & Compression Efficiency

**Date:** 2026-04-21  
**Project:** wsnsim (Discrete-Event Simulator for WSN)  
**Subject:** Performance Analysis of Robust Delta-Encoding and Weighted Aggregation  

## 1. Executive Summary
To extend the lifetime of wireless sensor nodes, we implemented and evaluated a robust in-network data aggregation pipeline. Experiments demonstrate that the combination of **Delta-Encoding**, **Threshold-based Filtering**, and **Periodic Resets** can reduce network traffic by **95% to 98%** while maintaining reconstruction accuracy (MSE < 0.02 in optimal configurations).

## 2. Methodology & Experimental Setup
*   **Ground Truth:** Synthetic sensor signal generated using a sine wave, an upward trend, and Gaussian noise ($\sigma = 0.05$), totaling 1,000 samples.
*   **Network Topology:** A 2-hop convergecast model where a Leaf Node sends data to an **Aggregating Router**, which processes and forwards data to the Sink.
*   **Aggregation Strategy:** `TreeDeltaAvgStrategy` using:
    *   **Window Size ($N$):** Number of samples (weight) aggregated into a single average.
    *   **Threshold ($T$):** Minimum absolute change required to trigger a transmission.
    *   **Refresh Interval ($R$):** Every $R$-th transmission is sent as an absolute value to prevent cumulative error (drift).
*   **Error Metric:** Mean Squared Error (MSE) between the original high-frequency sensor signal and the reconstructed signal at the Sink (using Zero-Order Hold).

## 3. Performance Metrics (Random Seed: 57)
| Scenario | Packets Sent | Reduction (CRR) | MSE (Accuracy) | Abs/Delta Ratio |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline (No Aggregation)** | 1000 | 0.0% | 0.00000 | 1000 / 0 |
| **Balanced (N=5, T=0.2, R=10)** | 33 | 96.7% | 0.01927 | 4 / 29 |
| **Aggressive (N=10, T=0.4, R=5)** | 16 | 98.4% | 0.06763 | 4 / 12 |

## 4. Key Findings & Analysis
1.  **Efficiency vs. Accuracy:** The **Threshold ($T$)** is the most potent parameter for energy saving. A threshold of 0.2 reduced traffic by over 96% with negligible visual impact on the reconstructed signal.
2.  **Drift Prevention:** The **Periodic Reset ($R$)** mechanism is crucial. By sending absolute values every 5-10 transmissions, we ensure that packet loss or calculation precision issues do not lead to permanent value offsets at the Sink.
3.  **Associativity through Weighting:** By utilizing **Sample Weights**, the aggregation becomes tree-independent. Intermediate routers can correctly merge data from different subtrees without biasing the global average.

## 5. Visualizations
The results are visually confirmed in `reports/figures/robust_aggregation_test.png`, showing that the reconstructed "Aggregated" signals closely follow the "Ground Truth" while ignoring minor noise fluctuations.

## 6. Technical Recommendations
*   **For Stable Environments (e.g., Indoor Temp):** Use $N=10, T=0.5, R=20$ to maximize battery life.
*   **For Dynamic Environments (e.g., Industrial Monitoring):** Use $N=3, T=0.1, R=5$ to ensure low latency and high sensitivity to sudden changes.
