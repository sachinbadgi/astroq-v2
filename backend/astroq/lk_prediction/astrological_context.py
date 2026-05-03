import logging
from typing import Optional, Any, List, Dict
from .astro_chart import AstroChart
from .data_contracts import ChartData, EnrichedChart, PlanetInHouse, RuleHit
from .state_ledger import StateLedger
from .lk_constants import ENEMIES, get_35_year_ruler, NATURAL_RELATIONSHIPS, PLANET_EXALTATION
from .lk_pattern_constants import MATURITY_AGE_PATTERN
from .dignity_engine import DignityEngine
from .dormancy_engine import DormancyEngine, DormancyState

logger = logging.getLogger(__name__)

from dataclasses import dataclass, field

@dataclass
class PlanetState:
    """
    DEEP MODULE: The total effective state of a planet.
    Leverage: Callers don't need to know IF a planet is dormant or how its 
    strength is scaled—they just ask for the final effective values.
    """
    name: str
    house: int
    natal_house: Optional[int]
    is_awake: bool
    strength: float
    dignity_multiplier: float
    recoil_multiplier: float
    complex_state: Any = None
    is_startled: bool = False

    @property
    def effective_strength(self) -> float:
        """Total strength after applying all state-based multipliers."""
        return self.strength * self.dignity_multiplier * self.recoil_multiplier


class UnifiedAstrologicalContext:
    """
    DEEP MODULE: The source of truth for all planetary states and lookups.
    Hides complexity of:
    1. Masnui vs Natal identity resolution.
    2. Dynamic state lookups (Dormancy, Dignity, Trauma).
    3. Multi-chart synchronization (Natal + Annual).
    4. Magnitude normalization and scaling.
    """

    def __init__(
        self,
        enriched: EnrichedChart,
        natal_chart: Optional[ChartData] = None,
        ledger: Optional[StateLedger] = None,
        config: Any = None
    ):
        self.enriched = enriched
        self.chart = AstroChart(enriched.source)
        self.natal_chart = AstroChart(natal_chart) if natal_chart else None
        self.ledger = ledger or StateLedger()
        self.dormancy_engine = DormancyEngine()
        self.dignity_engine = DignityEngine(config)
        self.config = config

        self.age = self.chart.period
        self.chart_type = self.chart.type

        # Scaling constants
        self.boost_scaling = config.get("rules.boost_scaling", fallback=0.04) if config else 0.04
        self.penalty_scaling = config.get("rules.penalty_scaling", fallback=0.15) if config else 0.15

        # Lazy cache for NatalFateView domain classifications
        self._fate_type_cache: Optional[Dict[str, str]] = None
        self._planet_state_cache: Dict[str, PlanetState] = {}

    def get_planet(self, planet_name: str) -> Optional[PlanetState]:
        """
        Returns the full effective state of a planet.
        Caches the result for the lifetime of the context.
        """
        if planet_name in self._planet_state_cache:
            return self._planet_state_cache[planet_name]

        house = self.get_house(planet_name)
        if house is None:
            return None

        base_name = self.resolve_base_planet(planet_name)
        state = self.get_complex_state(planet_name)
        
        ps = PlanetState(
            name=planet_name,
            house=house,
            natal_house=self.get_natal_house(planet_name),
            is_awake=state.is_awake,
            strength=self.get_planet_strength(planet_name),
            dignity_multiplier=self.get_dignity_multiplier(planet_name),
            recoil_multiplier=self.get_recoil_multiplier(planet_name),
            complex_state=state,
            is_startled=state.is_startled
        )
        self._planet_state_cache[planet_name] = ps
        return ps

    def resolve_base_planet(self, planet_name: str) -> str:
        """Strips 'Masnui ' prefix to get the underlying planetary archetype."""
        return planet_name.replace("Masnui ", "") if planet_name.startswith("Masnui ") else planet_name

    def get_house(self, planet_name: str) -> Optional[int]:
        """Returns the current house of a planet (handles Masnui fallback)."""
        return self.chart.get_house(planet_name)

    def get_natal_house(self, planet_name: str) -> Optional[int]:
        """Returns the natal house of a planet archetype."""
        if not self.natal_chart: return None
        base_name = self.resolve_base_planet(planet_name)
        return self.natal_chart.get_house(base_name)

    def is_awake(self, planet_name: str) -> bool:
        """Deep check for planetary dormancy using DormancyEngine."""
        house = self.get_house(planet_name)
        if not house: return False
        ppos = {p: self.get_house(p) for p in self.chart.planets}
        return self.dormancy_engine.is_awake(planet_name, house, ppos, current_age=self.age)

    def get_complex_state(self, planet_name: str) -> DormancyState:
        """Returns the full activation state including sustenance and startle triggers."""
        house = self.get_house(planet_name)
        ppos = {p: self.get_house(p) for p in self.chart.planets}
        return self.dormancy_engine.get_complex_state(planet_name, house or 0, ppos, current_age=self.age)

    def has_180_degree_block(self, planet_name: str) -> bool:
        """Checks if a natural enemy is placed exactly 180 degrees away (house + 6 mod 12)."""
        house = self.get_house(planet_name)
        if not house: return False
        
        enemy_house = house + 6
        if enemy_house > 12: enemy_house -= 12
            
        enemies_in_opposition = self.chart.get_occupants(enemy_house)
        if not enemies_in_opposition: return False
            
        base_name = self.resolve_base_planet(planet_name)
        planet_enemies = NATURAL_RELATIONSHIPS.get(base_name, {}).get("Enemies", [])
        
        for opp_planet in enemies_in_opposition:
            opp_base = self.resolve_base_planet(opp_planet)
            if opp_base in planet_enemies:
                if house in PLANET_EXALTATION.get(base_name, []): continue
                if enemy_house in PLANET_EXALTATION.get(opp_base, []): continue
                return True
        return False

    def check_maturity_age(self, planet_name: str) -> bool:
        """Returns True if the planet has reached its maturity age."""
        base_name = self.resolve_base_planet(planet_name)
        maturity_ages = MATURITY_AGE_PATTERN.get("maturity_ages", {})
        mat_age = maturity_ages.get(base_name, 0)
        return self.age >= mat_age

    def calculate_rule_magnitude(self, hit: RuleHit) -> float:
        """
        DEEP MODULE: Centralized magnitude calculation.
        Applies base scaling, annual dignity, cycle rulers, and recoil multipliers.
        """
        mag = hit.magnitude
        targets = hit.primary_target_planets
        
        # Ensure targets is iterable and not a bool
        if not hasattr(targets, "__iter__") or isinstance(targets, bool):
            targets = []

        # 1. Apply Base Scaling if magnitude is None (Dynamic Scaling)
        if mag is None:
            base = self.boost_scaling if hit.scoring_type == "boost" else self.penalty_scaling
            mag = self._apply_scale_to_base(getattr(hit, "scale", "minor"), base)

        # 2. Config Overrides
        if self.config:
            override_key = f"weight.{hit.rule_id}"
            w = self.config.get(override_key)
            if w is not None:
                mag *= float(w)

        # 3. Apply Multipliers from targets
        if targets:
            multipliers = []
            for p_name in targets:
                p_state = self.get_planet(p_name)
                if p_state:
                    # Leverage: The context knows how to merge dignity and recoil
                    multipliers.append(p_state.dignity_multiplier * p_state.recoil_multiplier)
            
            if multipliers:
                avg_mult = sum(multipliers) / len(multipliers)
                mag *= avg_mult

        # 4. 35-Year Cycle Ruler Modifier
        if self.age and targets:
            mag *= self.get_cycle_ruler_multiplier(list(targets))

        return mag

    def _apply_scale_to_base(self, scale: str, base_scaling: float) -> float:
        sc = scale.lower()
        if sc == "minor": return base_scaling * 1.0
        if sc == "moderate": return base_scaling * 2.0
        if sc == "major": return base_scaling * 3.0
        if sc in ("extreme", "deterministic"): return base_scaling * 4.0
        return base_scaling * 1.0

    def get_dignity_multiplier(self, planet_name: str) -> float:
        """Returns the annual dignity multiplier based on rotation from natal position."""
        if self.chart_type == "Birth": return 1.0
        
        base_name = self.resolve_base_planet(planet_name)
        natal_h = self.get_natal_house(base_name)
        
        if not natal_h: return 1.0
        
        return self.dignity_engine.get_annual_dignity_multiplier(base_name, natal_h, self.age)

    def get_planet_ledger_state(self, planet_name: str) -> Any:
        """Returns the current trauma/modifier state from the StateLedger."""
        base_name = self.resolve_base_planet(planet_name)
        return self.ledger.get_planet_state(base_name)

    def get_recoil_multiplier(self, planet_name: str) -> float:
        """Returns the trauma-induced recoil multiplier."""
        base_name = self.resolve_base_planet(planet_name)
        return self.ledger.get_recoil_multiplier(base_name, self.age)

    @property
    def house_status(self) -> Dict[str, str]:
        """Returns the occupancy status of all 12 houses."""
        return self.chart.house_status

    def get_enriched_data(self, planet_name: str) -> Dict[str, Any]:
        """Returns enrichment metadata (Kaayam, Dharmi, etc.) from the EnrichedChart."""
        base_name = self.resolve_base_planet(planet_name)
        return self.enriched.planet_strengths.get(base_name, {})

    def get_planet_strength(self, planet_name: str) -> float:
        """
        Returns the annual strength_total for a planet.
        O(1) lookup from EnrichedChart.planet_strengths.
        Returns 0.0 if the planet is not found.
        """
        base_name = self.resolve_base_planet(planet_name)
        planet_data = self.enriched.planet_strengths.get(base_name, {})
        return float(planet_data.get("strength_total", 0.0))

    def get_cycle_ruler_multiplier(self, planet_names: List[str]) -> float:
        """Calculates the 35-year cycle ruler bonus or friction."""
        if not self.age: return 1.0
        
        cycle_ruler = get_35_year_ruler(self.age)
        base_names = {self.resolve_base_planet(p) for p in planet_names}
        
        if cycle_ruler in base_names:
            return 1.20   # Period ruler delivers the rule
        
        # Check for hostility
        for p in base_names:
            if cycle_ruler in ENEMIES.get(p, []):
                return 0.85 # Hostility friction
                
        return 1.0

    def get_fate_type_for_domain(self, domain: str) -> str:
        """
        Returns the natal fate classification for a domain.
        Possible values: "GRAHA_PHAL", "RASHI_PHAL", "HYBRID", "NEITHER".
        """
        if not self.natal_chart:
            return "RASHI_PHAL"

        if self._fate_type_cache is None:
            from .natal_fate_view import NatalFateView
            view = NatalFateView()
            entries = view.evaluate(self.natal_chart.data, include_neither=True)
            self._fate_type_cache = {
                e["domain"]: (
                    "RASHI_PHAL" if e["fate_type"] == "HYBRID" else e["fate_type"]
                )
                for e in entries
            }

        domain_key = domain.strip().lower()
        if domain_key in self._fate_type_cache:
            return self._fate_type_cache[domain_key]
        for k, v in self._fate_type_cache.items():
            if domain_key in k or k in domain_key:
                return v
        return "RASHI_PHAL"


