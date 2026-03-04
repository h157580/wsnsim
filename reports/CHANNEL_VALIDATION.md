# Rádiós Csatorna Modell Dokumentáció és Validáció

Ez a dokumentum a `wsnsim` projekt rádiós terjedési modelljének elméleti hátterét és annak manuális validációját tartalmazza.

## 1. Elméleti Modell
A szimuláció a **Log-distance Path Loss** modellt használja, kiegészítve log-normális árnyékolással (shadowing) és nem-koherens FSK moduláció alapú hibaaránnyal.

### Útvonalveszteség (Path Loss)
A csillapítás számítása a referencia-távolság ($d_0$) alapján történik:
$$PL(d) = \begin{cases} 
PL_{d0} & 	ext{ha } d \le d_0 
PL_{d0} + 10n \log_{10}(\frac{d}{d_0}) & 	ext{ha } d > d_0 
\end{cases}$$

### Bit hibaarány (BER)
Nem-koherens FSK moduláció esetén a BER és az SNR (lineáris) kapcsolata:
$$BER = 0.5 \cdot e^{-0.5 \cdot SNR_{linear}}$$

### Csomagvételi arány (PRR)
A csomagvételi valószínűség a $L$ hosszúságú csomag esetén:
$$PRR = (1 - BER)^L$$

---

## 2. Konfigurációs Alapértékek
A számítások során az alábbi paramétereket használtuk:
* **Referencia távolság ($d_0$):** 1.0 m
* **Veszteség $d_0$-nál ($PL_{d0}$):** 40.0 dB
* **Útvonalveszteség kitevő ($n$):** 3.0
* **Zajszint ($P_{noise}$):** -105 dBm ($3.16 	imes 10^{-11}$ mW)
* **Csomaghossz ($L$):** 1024 bit

---

## 3. Manuális Validációs Pontok

Az alábbi táblázat tartalmazza a kód ellenőrzéséhez szükséges fix pontokat (árnyékolás nélkül, `use_shadowing=False`).

| Paraméter | 1. Pont (Referencia tartomány) | 2. Pont (Átmeneti zóna) |
| :--- | :--- | :--- |
| **Bemenet: Távolság ($d$)** | 1.0 m | 10.0 m |
| **Bemenet: Adóteljesítmény ($P_{tx}$)** | 1.0 mW (0 dBm) | 0.00316 mW (-25 dBm) |
| Számított Path Loss ($PL$) | 40.0 dB | 70.0 dB |
| Vett teljesítmény ($P_{rx}$) | -40.0 dBm | -95.0 dBm |
| Jel-zaj arány ($SNR_{dB}$) | 65.0 dB | 10.0 dB |
| Jel-zaj arány ($SNR_{linear}$) | 3,162,277.6 | 10.0 |
| Bit hibaarány ($BER$) | $\approx 0$ | 0.003369 |
| **Elvárt PRR** | **1.0000** | **0.0308** |

### Validációs megjegyzések:
1. **1. Pont:** Azt hivatott igazolni, hogy közeli távolságon és nagy teljesítménynél a vétel tökéletes, a logaritmus számítások nem okoznak alulcsordulást.
2. **2. Pont:** A "szürke zónát" teszteli. Ha a kód 0.0308 (± 0.0001) értéket ad vissza, akkor a dBm/mW konverziók és a hatványozás sorrendje is helyes.

---

## 4. Implementációs javaslat a teszteléshez
A fenti pontok ellenőrizhetőek az alábbi `pytest` kódrészlettel:

```python
def test_manual_validation_points(model):
    # 1. Pont: Referencia
    prr1 = model.calculate_prr(tx_power_mw=1.0, distance=1.0, use_shadowing=False)
    assert pytest.approx(prr1, abs=1e-4) == 1.0

    # 2. Pont: Átmeneti zóna
    prr2 = model.calculate_prr(tx_power_mw=0.00316, distance=10.0, use_shadowing=False)
    assert pytest.approx(prr2, abs=1e-4) == 0.0308
```
