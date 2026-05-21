# 🔌 ESP32 Hardware Wiring Diagram

## 📋 Components List

| Thành phần | Số lượng | Giá | Mục đích |
|-----------|---------|-----|---------|
| **ESP32-WROOM-32 DevKit** | 1 | 100-150K ₫ | Main Board |
| **LED (5mm)** | 1 | 1K ₫ | Indicator |
| **Resistor 220Ω** | 1 | 0.5K ₫ | LED protection |
| **Buzzer 5V** | 1 | 10-15K ₫ | Alert sound |
| **Breadboard** | 1 | 20-30K ₫ | Prototyping |
| **Jumper Wires** | 20 | 10K ₫ | Connections |
| **USB Micro Cable** | 1 | 15K ₫ | Power + Upload |
| **Power Bank / USB Charger** | 1 | - | Power ESP32 |

**Total:** ~150-200K ₫

---

## 🎯 GPIO Pin Assignment (từ esp32_simple.ino)

```cpp
const int LED_PIN = 19;        // Red LED
const int BUZZER_PIN = 18;     // 5V Buzzer
```

| Chức năng | Pin GPIO | Loại | Điện áp |
|----------|----------|------|---------|
| LED | GPIO19 | Digital Output | 3.3V |
| Buzzer | GPIO18 | Digital Output | 5V |
| GND | GND | Ground | 0V |
| VCC | 5V/3.3V | Power | - |

---

## 📐 Simple Wiring Diagram (ASCII)

```
                    ╔════════════════════╗
                    ║   ESP32 Board      ║
                    ║                    ║
        EN  ──────  ║ EN              GND ║  ──── GND (Black)
                    ║                    ║
                    ║ GPIO19 (LED)       ║
         ┌──────────║                    ║
         │          ║ GPIO18 (Buzzer)    ║
         │          ║                    ║
         │    3.3V ─╫─ 3V3              5V ║  ──── 5V (Red)
         │   (Brown)║                    ║        (USB Power)
         │          ║ GND               GND ║  ──── GND
         │          ╚════════════════════╝
         │
    ┌────┴────────────────┐
    │   Breadboard        │
    │                    │
    │  GPIO19 ┌─ A1      │
    │         │          │
    │     ┌───┴──────┐    │
    │     │ 220Ω    │    │
    │    A2──────B2   │   │
    │     └───┬──────┘    │
    │         │          │
    │        B1 LED Anode (Long leg)
    │         │  LED (+)  │
    │        C1 LED Cathode (Short leg)
    │         │  LED (-)  │
    │         │          │
    │        C3 GND ──────┘
    │         │
    └─────────┘
```

---

## 🔴 Detailed Wiring - LED (GPIO19)

### Components:
- ESP32 GPIO19
- LED (5mm Red)
- Resistor 220Ω

### Steps:

```
1. LED Long Leg (Anode = +)
   ├─ Resistor 220Ω
   └─ Breadboard Positive Rail
       └─ ESP32 GPIO19

2. LED Short Leg (Cathode = -)
   └─ GND (Black wire)
       └─ ESP32 GND

Diagram:
ESP32 GPIO19 ──→ 220Ω Resistor ──→ LED (+) ──┐
                                              │
                                    Breadboard│
                                              │
                                ESP32 GND ←──┘
```

---

## 🔊 Detailed Wiring - Buzzer (GPIO18)

### Components:
- ESP32 GPIO18
- Buzzer 5V (có 2 chân)

### Steps:

```
1. Buzzer (+) Red Wand
   └─ 5V (Red USB Power)
       └─ ESP32 5V pin

2. Buzzer (-) Black Wand
   ├─ GPIO18 Control Signal
   └─ GND Return

Diagram:
       ┌─── 5V (USB Power, Red) ──┐
       │                          │
   [Buzzer +]                  [Buzzer -]
       │                          │
     5V                         GPIO18
      │                           │
   ESP32──────────────────────────┘
```

---

## 📍 ESP32 Pin Layout (Top View)

```
                     USB Micro
                        │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴───┬───────────────────────┬───┴────┐
    │ EN  GND│                       │3V3  GND│
    │        │                       │        │
    │ TX   RX│    ESP32-WROOM-32    │GND  D33│
    │        │     (Top View)       │        │
    │ D35 D34│                       │D32  D25│
    │        │                       │        │
    │ D39 D36│                       │D26  D27│
    │        │                       │        │
    │ D4   D2│                       │D14  D12│
    │        │                       │        │
    │ D15  D8│                       │ D13 D9 │
    │        │                       │        │
    │ D7   D6│                       │ D11 D10│
    │        │                       │        │
    │ D5   D3│                       │ D1  D0 │
    │        │                       │        │
    │ D18 D17│  ← GPIO18 (Buzzer)   │        │
    │        │  ← GPIO19 (LED)      │        │
    │ D19 D16│                       │5V   GND│
    └────────┴───────────────────────┴────────┘

Legend:
GPIO18 = Buzzer Control
GPIO19 = LED Control
5V     = 5V Power (from USB)
GND    = Ground (Black wire)
3V3    = 3.3V Power (NOT used in this project)
```

---

## 🧵 Complete Wiring Table

| ESP32 Pin | Connection | Component | Wire Color |
|-----------|-----------|-----------|-----------|
| **GPIO18** | Buzzer (-) Control | Buzzer Black | White/Orange |
| **GPIO19** | 220Ω Resistor | LED (+) | Green/Blue |
| **GND** | LED (-) Return | LED Short Leg | Black |
| **GND** | Buzzer GND Return | Buzzer Circuit | Black |
| **5V** | Buzzer (+) Power | Buzzer Red | Red |
| **GND** | Breadboard GND | Common Ground | Black |

---

## 🛠️ Assembly Steps

### Step 1: Prepare Breadboard
```
Layout:
Positive Rail (Red) ─── [5V from USB]
Negative Rail (Black) ─── [GND]
```

### Step 2: Install LED Circuit
```
1. Insert LED into breadboard
   - Long leg (Anode = +) → Column A
   - Short leg (Cathode = -) → Column B

2. Connect 220Ω Resistor
   - One end → Column A (with LED +)
   - Other end → Positive Rail or directly to GPIO19

3. LED Short Leg → GND (Negative Rail)

Breadboard View:
     A    B    C    D
  +──────────────────+
1 │220Ω  │    │    │ ← 220Ω Resistor
  ├─────LED───┤    │ ← LED
2 │  │  X    │    │ ← LED (X = LED in holes)
  │  └─────GND───────+ ← Black wire to GND
  +──────────────────+

(X = LED position in breadboard)
```

### Step 3: Install Buzzer
```
Buzzer has 2 Wands:
- Red (+) → 5V USB Power
- Black (-) → GPIO18 (Control Signal)

Connections:
1. Buzzer Red → USB Power 5V (Red wire)
2. Buzzer Black → ESP32 GPIO18 (White/Orange wire)
3. Buzzer Black also connects to GND (circuit return)
```

### Step 4: Connect ESP32
```
USB Connections:
1. USB Micro (5V) → ESP32 5V pin
2. GND wire → ESP32 GND pin

GPIO Connections:
1. GPIO19 → 220Ω → LED (+)
2. GPIO18 → Buzzer (-) control

GND Connections (Black Wires):
- LED (-) → GND
- Buzzer circuit → GND
- All GND points connected together
```

---

## 📸 Real Wiring Photo Guide

### For LED:
```
ESP32 GPIO19 Pin
    ↓
   [Wire] (Blue/Green)
    ↓
Breadboard Row
    ↓
[220Ω Resistor]
    ↓
LED Anode (Long leg) ← INSERT into breadboard
    ↓
LED Cathode (Short leg) → Connect to GND (Black wire)
```

### For Buzzer:
```
Option 1: Direct to GPIO (Recommended for 5V Buzzer)
ESP32 GPIO18 → Buzzer Black Wire (control)
ESP32 5V → Buzzer Red Wire (power)
ESP32 GND → Buzzer GND (return)

Option 2: Via Relay (if 12V Buzzer)
(Not needed for 5V passive buzzer in this project)
```

---

## ✅ Verification Checklist

Before uploading firmware:

- [ ] LED installed correctly (long leg to 220Ω)
- [ ] 220Ω Resistor connected in series with LED
- [ ] LED short leg connected to GND
- [ ] Buzzer red wire connected to 5V (USB Power)
- [ ] Buzzer black wire connected to GPIO18
- [ ] All GND wires connected together (common ground)
- [ ] No bare wires touching each other (short circuit)
- [ ] USB cable connected to ESP32
- [ ] No visible damage to components

---

## 🧪 Physical Test (Before Code)

```bash
# 1. Test LED visibility
- Shine light on LED
- LED should have clear red/green color
- Check polarity (long leg is +)

# 2. Test Buzzer sound
- Listen for beep when powered
- Check buzzer has correct voltage (5V)

# 3. Test Continuity
- Use multimeter Ohms mode
- LED: Should show ~200Ω (with resistor)
- Buzzer: Should show ~10-20Ω
```

---

## ⚠️ Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| LED backwards | Won't light up | Swap LED legs |
| Resistor value wrong | LED too dim/bright | Use exactly 220Ω |
| Buzzer polarity wrong | No sound | Check red/black wires |
| Missing GND connection | LED flickers, buzzer weak | Connect all GND together |
| Wrong GPIO pins | Nothing works | Check esp32_simple.ino pins |
| 3.3V instead of 5V | Buzzer too weak | Use 5V USB power |

---

## 🔌 Connector Pinout Reference

### ESP32-WROOM-32 Pinout (30 pins, 15 each side):

```
Left Side (15 pins):          Right Side (15 pins):
GND   1                       3.3V  16
(reserved) 2                  GND   17
D15   3                       D33   18
D2    4                       D34   19
D4    5                       D35   20
D5    6                       GND   21
D18   7 ← BUZZER              D39   22
D19   8 ← LED                 D36   23
D21   9                       EN    24
RX0   10                      5V    25 ← USB POWER
TX0   11                      GND   26
D22   12                      D23   27
D3    13                      D1    28
D1    14                      D0    29
D6    15                      GND   30
```

---

## 📊 Electrical Specifications

| Component | Voltage | Current | Power |
|-----------|---------|---------|-------|
| ESP32 | 5V USB | 100-200mA | 0.5-1W |
| LED (Red 5mm) | 2V | 20mA | 0.04W |
| 220Ω Resistor | Variable | ~15mA | 0.05W |
| Buzzer 5V | 5V | 30-50mA | 0.15-0.25W |
| **Total** | 5V | ~150-250mA | **0.74W** |

✅ **Safe - USB can provide 500mA**

---

## 🎯 Quick Reference

**Just Remember:**
```
GPIO19 → LED (with 220Ω resistor) → GND
GPIO18 → Buzzer (-) 
5V → Buzzer (+)
GND → Common Ground
```

**That's it!** 🎉

