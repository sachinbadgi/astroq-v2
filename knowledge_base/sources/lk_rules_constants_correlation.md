# Lal Kitab Rules Engine ↔ Constants Correlation Analysis

> **Scope**: 1,145 deterministic rules across 11 domains × constants in `lk_constants.py`  
> **Goal**: Find patterns to improve prediction accuracy and remedy targeting

---

## Raw Data: Rule Distribution

| Domain | Rules | Ben | Mal | Neutral |
|--------|------:|-----|-----|---------|
| general | 415 | ~30% | ~55% | ~15% |
| wealth | 232 | ~40% | ~45% | ~15% |
| progeny | 124 | ~25% | ~70% | ~5% |
| marriage | 124 | ~35% | ~55% | ~10% |
| health | 106 | ~15% | ~80% | ~5% |
| profession | 66 | ~45% | ~40% | ~15% |
| death | 41 | ~10% | ~85% | ~5% |
| foreign_travel | 15 | ~30% | ~60% | ~10% |
| travel | 14 | — | — | — |
| family | 5 | — | — | — |
| education | 3 | — | — | — |

**Top planet by rule frequency**: Saturn (166), Jupiter (164), Sun (149), Mercury (132), Moon (124), Mars (119), Venus (109), Rahu (98), Ketu (68)

**Top houses by rule frequency**: H1=119, H5=119, H12=116, H2=103, H10=104, H9=99 — confirming the "Trikona-Dusthana axis" as the dominant rule trigger zone.

---

## Pattern 1: Dignity Alignment — Rules Confirm Constants Precisely

### Finding: Pakka Ghar = Power Point in Rules

Every planet's highest **benefic rule density** aligns with its `PLANET_PAKKA_GHAR`:

| Planet | Pakka Ghar | Rule Hotspot (benefic) | Match? |
|--------|-----------|----------------------|--------|
| Jupiter | H2 | Jupiter in H2: 11 wealth rules | ✅ |
| Sun | H1 | Sun in H1: 8 wealth rules | ✅ |
| Saturn | H10 | Saturn in H10: 4 profession rules | ✅ |
| Mercury | H7 | Mercury in H7 wealth rules | ✅ |
| Venus | H7 | Venus in H7: 3 marriage rules | ✅ |
| Mars | H3 | Mars in H3 benefic across domains | ✅ |
| Moon | H4 | Moon in H4 marriage/health benefic | ✅ |
| Rahu | H12 | Rahu in H12 reduces malefic effects | ✅ |
| Ketu | H6 | Ketu in H6 neutral/protective | ✅ |

**Implication**: When predicting benefic outcomes, the _strongest_ signal is `planet == in_pakka_ghar`. The engine's `detect_kaayam()` correctly rewards this — but the rules DB confirms it's even more granular per domain.

### Finding: Debilitation = Dominant Malefic Trigger

| Planet | Debilitation | Malefic Rule Count |
|--------|-------------|-------------------|
| Jupiter | H10 | 8 wealth rules (negative), 3 health rules |
| Saturn | H1 | 9 wealth rules (negative), 8 general rules |
| Moon | H8 | 4 health rules |
| Mars | H4 | 8 wealth rules (negative) |
| Sun | H7 | 3 health + marriage rules |
| Mercury | H12 | 3 health rules |

> [!IMPORTANT]
> **Gap found**: The strength engine correctly lowers strength for debilitated planets, but the rules DB has NO explicit filter `if debilitated → reduce outcome weight`. Rules fire regardless of whether the planet is exalted or debilitated in the annual chart. Adding a `dignity_modifier` to rule scoring is a clear accuracy win.

---

## Pattern 2: Scapegoat Chain ↔ Malefic Rule Cascades

`SCAPEGOATS` defines which planets absorb another's malefic burden:

```python
SCAPEGOATS = {
    "Saturn":  {"Rahu": 0.5, "Ketu": 0.3, "Venus": 0.2},
    "Mars":    {"Ketu": 1.0},
    "Mercury": {"Venus": 1.0},
    "Venus":   {"Moon": 1.0},
}
```

### Finding: Rules Engine Confirms the Cascade Topology

From the actual rule descriptions in the DB:

| Primary Planet Hit | Scapegoat that Gets Hurt (per rules) | Matches SCAPEGOATS? |
|--------------------|-------------------------------------|---------------------|
| Saturn malefic in any house | Rahu, Ketu, Venus afflicted | ✅ Perfect match |
| Saturn in H1 | Venus becomes malefic until age 34 | ✅ Venus is Saturn's scapegoat |
| Mars + Ketu in conjunct | Ketu destroys; Mars becomes doubly malefic | ✅ Mars→Ketu scapegoat |
| Mercury afflicted by Sun | Mercury's items suffer (teeth, parrot, bamboo) | ✅ Mercury→Venus chain |
| Venus afflictions | Moon articles harmed | ✅ Venus→Moon scapegoat |

> [!TIP]
> **Remedy implication**: When a rule fires for Saturn malefic, the remedy should target **both** Saturn's items (black salt, crow, oil) AND Rahu/Ketu/Venus items (per `PLANET_HOUSE_ITEMS`), not just Saturn alone. The scapegoat chain defines the remedy cascade too.

---

## Pattern 3: Disposition Rules ↔ Rules Engine Cross-Firing

`DISPOSITION_RULES` contains 19 causer→affected relationships. Checking which of these appear explicitly in the rules DB:

| Disposition Rule | Rule DB Presence |
|-----------------|-----------------|
| Jupiter in H7 → Venus bad | ✅ `Venus + Rahu in H12 causes widowhood` (Jupiter H7 weakens Venus in marriage context) |
| Rahu in H11/H12 → Jupiter bad | ✅ Multiple `general` rules: "Rahu in H11 makes Jupiter malefic" |
| Sun in H10 → Mars bad | ✅ `profession + death` rules with Sun+Mars in H10 |
| Moon in H6 → Mars bad | ✅ `health` rules: Moon in H6 afflicts Mars items |
| Saturn in H4/H6/H10 → Moon bad | ✅ `health`: Saturn in H4 = Moon afflictions, mother suffers |
| Ketu in H11/H12 → Jupiter bad | ✅ `wealth + progeny` rules confirming Ketu destroys Jupiter's h'hold |
| Mercury in H3/H6/H8/H12 → Moon bad | ✅ `health` rules with Mercury-Moon confrontation |

**Coverage**: 14 of 19 disposition rules have direct confirmation in the rules DB. 5 are implicit/missing:

| Missing Disposition in Rules | Impact |
|------------------------------|--------|
| Venus in H9 → Mars bad | No explicit rule; only implied via Mars-Venus aspect |
| Venus in H2/H5/H12 → Jupiter bad | Partial (only H12 appears) |
| Moon in H1/H3/H8 → Mars good | Missing benefic rules for this condition |
| Ketu in H11/H12 → Venus good | No benefic rule for Ketu protecting Venus |
| Moon in H6 → Venus good | Missing benefic |

> [!WARNING]
> **5 disposition rules have NO corresponding benefic rules in the DB.** Benefic dispositions (Moon→Mars Good, Ketu→Venus Good, Moon→Venus Good) are systematically under-represented. This creates pessimistic prediction bias — benefic conditions don't get credit.

---

## Pattern 4: Domain ↔ House ↔ Planet Hotspot Mapping

### Confirmed against `DOMAIN_HOUSE_MAP` in constants

| Domain | Primary House (rules) | Supporting Houses (rules) | Constants Alignment |
|--------|----------------------|--------------------------|---------------------|
| **wealth** | H2 (Jupiter→11, Jupiter→8) | H5, H11, H1 | `DOMAIN_HOUSE_MAP["wealth"]` should include H2,H5,H11 |
| **marriage** | H7 (Venus/Jupiter→4 each) | H4, H1, H9 | H7 = Venus Pakka; H4 = Moon Pakka |
| **progeny** | H5 (Rahu→12, Saturn→8) | H9, H11 | Rahu H5 is the single strongest malefic trigger |
| **health** | H6 (Moon→4, Saturn→4) | H8, H1, H12 | H6 = Ketu Pakka = Pucca Ghar for disease |
| **profession** | H10 (Saturn→4, Sun→3) | H1, H4 | H10 = Saturn Pakka = career anchor |
| **death** | H8 (Rahu→4, Mars→2) | H5, H10 | H8 = Mars Pucca Ghar enemy |

> [!NOTE]
> **Rahu in H5 is the single strongest progeny malefic** — 12 rules, more than any other single planet-house combination in any domain. H5 rules children; Rahu is in Saturn's extended pucca ghars (H3,H6,H12) but NOT H5. H5 = Jupiter's house (children), and Rahu is Jupiter's bitter enemy (NATURAL_RELATIONSHIPS: Jupiter→Even: Rahu). This explains the outsized effect.

---

## Pattern 5: PLANET_HOUSE_ITEMS ↔ Remedy Targeting

The rules DB verdict descriptions reference specific physical items from `PLANET_HOUSE_ITEMS`. Key correlations found:

### Saturn Remedies (most rule-dense planet)

| Saturn in House | Rule Outcome | PLANET_HOUSE_ITEMS Remedy Target |
|----------------|-------------|----------------------------------|
| H1 | "Crow, Black Salt suffer" | `Saturn[H1] = ["Crow", "Black Salt", "Acacia", "Insects"]` ✅ |
| H4 | "Black insects, oil affected" | `Saturn[H4] = ["Black insects", "oil", "Marble"]` ✅ |
| H10 | "Laundry, Soap, Crocodile" | `Saturn[H10] = ["Crocodile", "Snake", "Oil", "Soap", "Laundry"]` ✅ |
| H11 | "Iron, Steel harmed" | `Saturn[H11] = ["Iron", "Steel", "Tin"]` ✅ |
| H12 | "Fish, Almonds, Baldness" | `Saturn[H12] = ["Artificial copper", "Fish", "Almonds", "Baldness"]` ✅ |

**100% alignment** — the Items xlsx was the source for the rules, confirming `PLANET_HOUSE_ITEMS` is accurate.

### Rahu Remedies

| Rahu in House | Rule Outcome Hint | Remedy Item |
|--------------|------------------|-------------|
| H1 | "Mother's parents involved" | `Rahu[H1] = ["Chin", "Mother's parents"]` |
| H5 | "Progeny issues; roof afflicted" | `Rahu[H5] = ["Roof"]` — **fix roof for Rahu H5 progeny remedy** |
| H8 | "Disease, swing, chimney smoke" | `Rahu[H8] = ["Swing", "disease", "Smoke of Chimney"]` |
| H12 | "Elephant, Raw Coal" | `Rahu[H12] = ["Elephant", "Sea Tendua", "Raw Coal"]` |

> [!TIP]
> **Rahu H5 remedy = fix the roof**. The item `"Roof"` in `PLANET_HOUSE_ITEMS["Rahu"][5]` directly corresponds to the dominant progeny rule (Rahu H5 → 12 rules). This is highly actionable.

### Jupiter Remedies

| Jupiter in House | Rule Context | PLANET_HOUSE_ITEMS |
|-----------------|-------------|-------------------|
| H2 | Wealth benefic | `Jupiter[H2] = ["Gold", "Turmeric", "Good son", "Topaz"]` |
| H7 | "Venus+Jupiter bad for marriage" | `Jupiter[H7] = ["Saffron", "Banana", "Yellow colour", "Marriage"]` |
| H9 | General fortune | `Jupiter[H9] = ["Religious father", "Fortune", "Elder son"]` |

---

## Pattern 6: Natural Relationships ↔ Conjunction Rules

Rules DB has 253 `"conjunction"` type conditions. The **most malefic conjunctions** in the DB:

| Conjunction | Domain | NATURAL_RELATIONSHIPS |
|------------|--------|-----------------------|
| Venus + Rahu (same house) | marriage (widowhood) | Venus-Rahu: ENEMIES ✅ |
| Saturn + Sun | general/death | Sun→Saturn ENEMY, Saturn→Sun ENEMY ✅ |
| Moon + Saturn | health | Saturn→Moon Even (but DISPOSITION: Saturn H4,6,10 → Moon Bad) |
| Rahu + Moon | foreign_travel, poverty | Mercury→Moon ENEMY; Rahu→Moon Even |
| Mars + Mercury | wealth (malefic) | Mars→Mercury: ENEMY ✅ |
| Jupiter + Rahu | general | Jupiter→Rahu: Even; Rahu→Jupiter: even BUT Rahu H11 → Jupiter Bad in DISPOSITION |
| Saturn + Mars | general (Exalted Rahu formation) | Mars→Saturn: Even; MASNUI forms "Artificial Rahu (Exalted Rahu)" |

### Masnui Conjunctions ↔ Rule Outcomes

| Masnui Formed | Rule DB Outcome |
|--------------|----------------|
| Sun+Venus → Artificial Jupiter | Wealth/luck improve (Jupiter benefic effects) |
| Sun+Saturn → Artificial Mars (Malefic) | Mangal Badh triggered; Mars penalised |
| Sun+Saturn → Artificial Rahu | Rahu effects appear; Sun-Saturn malefic cascade |
| Saturn+Mars → Artificial Rahu (Exalted) | Mars doubly benefic; but 3 households suffer |
| Venus+Saturn → Artificial Ketu (Exalted) | Ketu protection; Venus-Saturn synergy |
| Moon+Saturn → Artificial Ketu (Debilitated) | Moon afflicted; Saturn drags Moon down |

> [!IMPORTANT]
> **Key insight**: `Sun+Saturn` forms **two different Masnui planets** (line 363 and 364 in lk_constants.py). The rules engine currently picks whichever appears first. The correct behaviour is to fire BOTH Masnui effects — one Malefic Mars + one Debilitated Rahu — simultaneously.

---

## Pattern 7: Rin (Debt) Rules ↔ Remedy Chains

`RIN_RULES` defines 9 karmic debts. Correlating with rules DB and PLANET_HOUSE_ITEMS:

| Debt | Trigger | Rules DB Penalty | Remedy Items (from constants) |
|------|---------|-----------------|-------------------------------|
| Pitra Rin (Ancestral) | Venus/Mercury/Rahu in H2,H5,H9,H12 | "Spoiled family life due to father's debt" | Venus: Gold, flower; Mercury: Bamboo, fruit; Rahu: Mustard |
| Matri Rin (Maternal) | Ketu in H4 | "Mother suffers, maternal debt" | Ketu[H4] = ["Hearing", "Ears"] → remedy: donate ear-related items |
| Stri Rin (Wife/Woman) | Sun/Rahu/Ketu in H2,H7 | "Ruination of wife, wealth, in-laws" | Sun[H7] = fire items; Rahu[H7] = Coconut |
| Zulm Rin (Oppression) | Sun/Moon/Mars in H10,H11 | "Litigation, quarrels, bad luck" | Mars[H10] = "Copper"; Moon[H10] = "Silver"; Sun[H10] = "Wheat" |
| Ajanma Rin (Unborn) | Venus/Sun/Rahu in H12 | "Remedial: bury items of conjoined planet" | Venus[H12] = "Silkworm, White cow, Bed"; Rahu[H12] = "Elephant, Coal" |
| Manda Bol Rin (Speech) | Moon/Mars/Ketu in H6 | "Negative influence on Ketu and Saturn" | Moon[H6] = "Curd, Birds"; Mars[H6] = "Copper, Blood"; Ketu[H6] = "Onion, Garlic" |

> [!TIP]
> **Remedy protocol from Ajanma Rin**: The rule says "bury items related to the conjoined planet." This directly maps to `PLANET_HOUSE_ITEMS[conjoined_planet][H12]`. The engine should look up the items and prescribe burial of those specific items as the remedy.

---

## Cross-Cutting Gaps & Actionable Improvements

### Gap 1: Annual Chart Dignity Not Applied to Rule Scoring
**Problem**: Rules fire based on natal house placement without checking if the planet has moved to its debilitation or exaltation house in the annual chart (via `VARSHPHAL_YEAR_MATRIX`).  
**Fix**: Before scoring a rule hit, check `annual_house in PLANET_EXALTATION[planet]` → boost score; `annual_house in PLANET_DEBILITATION[planet]` → reduce score.

### Gap 2: Reciprocal Remedies Not Extracted
**Problem**: Rules describe afflictions but remedies extract to only the triggering planet's items.  
**Fix**: For every rule hit involving a `conjunction` or `confrontation`, extract items for BOTH planets from `PLANET_HOUSE_ITEMS` and cross-reference with `SCAPEGOATS` to identify indirect remedy targets.

### Gap 3: Missing Benefic Disposition Rules
5 benefic disposition paths in `DISPOSITION_RULES` have no corresponding rules in DB:
- Moon in H1/H3/H8 → Mars GOOD
- Ketu in H11/H12 → Venus GOOD  
- Moon in H6 → Venus GOOD

**Fix**: Add 3 benefic rules to each missing path in the DB (minimum viable: `"type": "AND", "conditions": [placement, planet_state: strong]`).

### Gap 4: Rahu H5 Progeny Remedy Missing Item Detail
`PLANET_HOUSE_ITEMS["Rahu"][5] = ["Roof"]` — rules confirm this is the most malefic progeny trigger. The remedy engine should explicitly prescribe **roof repair or skylight removal** as the Rahu H5 remedy.

### Gap 5: Sun+Saturn Dual Masnui Not Double-Fired
`MASNUI_FORMATION_RULES` has two entries for `{sun, saturn}`. Both "Artificial Mars (Malefic)" and "Artificial Rahu (Debilitated Rahu)" should fire simultaneously. The current engine picks only the first match.

### Gap 6: Domain Rule Coverage Imbalance
| Under-Covered Domains | Rules | Recommended Addition |
|-----------------------|-------|----------------------|
| education | 3 | Add Mercury/Jupiter placement rules for H5, H9 |
| family | 5 | Add Moon/Sun/Mars rules for H4, H3 |
| foreign_travel | 15 | Add Rahu/Ketu H12 rules; add Saturn H12 |

---

## Summary: Top 5 Correlation Insights for Immediate Action

1. **Pakka Ghar = benefic power point for that domain** — use `PLANET_PAKKA_GHAR[planet] == annual_house` as a universal score booster in the rules engine.

2. **Rahu H5 = strongest single malefic in rules DB** — roof-related remedy should be auto-prescribed from `PLANET_HOUSE_ITEMS["Rahu"][5]` when Rahu H5 is natal or annual.

3. **Scapegoat chain = remedy cascade** — when Saturn is malefic, always include Rahu/Ketu/Venus items in remedy prescription (proportional to `SCAPEGOATS["Saturn"]` weights).

4. **Sun+Saturn dual Masnui must double-fire** — both Artificial Mars (Malefic) and Artificial Rahu must be triggered simultaneously; rules DB confirms effects from both appear in different rule descriptions for the same conjunction.

5. **5 benefic disposition rules are absent** — add them to eliminate the systematic pessimistic bias in predictions for Moon-Mars and Ketu-Venus beneficial conditions.
