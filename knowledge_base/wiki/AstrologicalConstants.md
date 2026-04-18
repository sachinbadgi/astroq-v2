# Lal Kitab Astrological Constants

This document explicitly defines the canonical lookups, relationships, and rule matrices that constitute the Lal Kitab 1952 foundation.

## 1. Core Dignities

| Planet | Pakka Ghar (Permanent) | Extended Pucca Ghars (For Remedies) | Exaltation (Peak) | Debilitation (Weak) |
|---|---|---|---|---|
| **Sun** | 1 | 1, 5 | 1 | 7 |
| **Moon** | 4 | 2, 4 | 2 | 8 |
| **Mars** | 3 | 3, 8, 10 | 10 | 4 |
| **Mercury** | 7 | 6, 7 | 6 | 12 |
| **Jupiter** | 2 | 2, 4, 5, 9, 11, 12 | 4 | 10 |
| **Venus** | 7 | 2, 7, 12 | 12 | 6 |
| **Saturn** | 10 | 7, 8, 10, 11 | 7 | 1 |
| **Rahu** | 12 | 3, 6, 12 | 3, 6 | 9, 12 |
| **Ketu** | 6 | 6, 9, 12 | 9, 12 | 3, 6 |

*(Note: The `Fixed House Lords` map identically matches the primary Pakka Ghar targets).*

## 2. Natural Relationships

| Planet | Friends | Enemies | Even (Neutral) |
|---|---|---|---|
| **Jupiter** | Sun, Moon, Mars | Venus, Mercury | Rahu, Ketu, Saturn |
| **Sun** | Jupiter, Mars, Moon | Venus, Saturn, Rahu | Mercury, Ketu |
| **Moon** | Sun, Mercury | Ketu | Venus, Saturn, Mars, Jupiter, Rahu |
| **Venus** | Saturn, Mercury, Ketu | Sun, Moon, Rahu | Mars, Jupiter |
| **Mars** | Sun, Moon, Jupiter | Mercury, Ketu | Venus, Saturn, Rahu |
| **Mercury** | Sun, Venus, Rahu | Moon | Saturn, Ketu, Mars, Jupiter |
| **Saturn** | Mercury, Venus, Rahu | Sun, Moon, Mars | Ketu, Jupiter |
| **Rahu** | Mercury, Saturn, Ketu | Sun, Venus, Mars | Jupiter, Moon |
| **Ketu** | Venus, Rahu | Moon, Mars | Jupiter, Saturn, Mercury, Sun |

## 3. Scapegoats (Negative Strength Redistribution)
When a planet carries a negative strength payload, it zeroes itself out and redistributes the burden to its scapegoats mathematically:
- **Saturn**: Rahu (50%), Ketu (30%), Venus (20%)
- **Mercury**: Venus (100%)
- **Mars**: Ketu (100%)
- **Venus**: Moon (100%)
- **Jupiter**: Ketu (100%)
- **Sun**: Ketu (100%)
- **Moon**: Jupiter (40%), Sun (30%), Mars (30%)

## 4. Fundamental Grammar & Debt Rules

### 4.1 Karmic Debts (Rin)
Debts activate if any of the target planets sit in any of the trigger houses:
- **Pitra Rin (Ancestral)**: Venus, Mercury, Rahu in H2, H5, H9, H12
- **Swayam Rin (Self)**: Venus, Rahu in H5
- **Matri Rin (Maternal)**: Ketu in H4
- **Stri Rin (Woman/Wife)**: Sun, Rahu, Ketu in H2, H7
- **Bhai-Bandhu Rin (Brother)**: Mercury, Ketu in H1, H8
- **Behen/Beti Rin (Sister/Daughter)**: Moon in H3, H6
- **Zulm Rin (Oppressive)**: Sun, Moon, Mars in H10, H11
- **Ajanma Rin (Unborn)**: Venus, Sun, Rahu in H12
- **Manda Bol Rin (Speech)**: Moon, Mars, Ketu in H6

### 4.2 Masnui (Artificial) Planet Conjunctions
When these pairs sit in the exact same house, they generate a third Artificial entity:
- **Sun + Venus** = Artificial Jupiter
- **Mercury + Venus** = Artificial Sun
- **Sun + Jupiter** = Artificial Moon
- **Rahu + Ketu** = Artificial Venus
- **Sun + Mercury** = Artificial Mars (Auspicious)
- **Sun + Saturn** = Artificial Mars / Rahu
- **Jupiter + Rahu** = Artificial Mercury
- **Venus + Jupiter** = Artificial Saturn (Ketu-like)
- **Mars + Mercury** = Artificial Saturn (Rahu-like)

## 5. Timing Matrices

### 5.1 35-Year Life Cycle Sub-Periods
- Age 1-6 = Saturn
- Age 7-12 = Rahu
- Age 13-15 = Ketu
- Age 16-21 = Jupiter
- Age 22-23 = Sun
- Age 24 = Moon
- Age 25-27 = Venus
- Age 28-33 = Mars
- Age 34-35 = Mercury

### 5.2 Planet Effective (Maturity) Ages
- **Jupiter**: 16
- **Sun**: 22
- **Moon**: 24
- **Venus**: 25
- **Mars**: 28
- **Mercury**: 34
- **Saturn**: 36
- **Rahu**: 42
- **Ketu**: 48

---

## 6. Graph Arrays (Aspects)

### 6.1 House-to-House Aspect Rules
Highlights of major geometric aspects:
- **House 1** casts 100% to **H7**
- **House 4** casts 100% to **H10**
- **House 3** casts 50% to **H9, H11**
- **House 5** casts 50% to **H9**

### 6.2 Asymmetric Point-Matrix (Aspect Strength)
A mathematically specific matrix evaluating hostility/alignment. Examples:
- `Saturn` casting on `Sun`: **-5.0**
- `Saturn` casting on `Mars`: **-5.0**
- `Jupiter` casting on `Sun`: **2.0**
- `Moon` casting on `Ketu`: **-5.0**

*(The complete float matrix and the 120-Year Varshphal Matrix mapping Ages to shifted graph vertices are stored extensively in code, and serve as the deterministic backbone for these definitions).*
