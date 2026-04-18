"""
Tests for Module 9: Physics Engine (Thermodynamic Diffusion & Mutability).
"""

import pytest
import numpy as np
from astroq.lk_prediction.physics_engine import PhysicsEngine
from astroq.lk_prediction.data_contracts import RuleHit

class TestPhysicsEngine:

    def test_physics_rin_drain(self):
        """Verify Rin-affected houses get 0.25 energy drain during Laplacian pass."""
        engine = PhysicsEngine()
        
        # Mock chart with Pitra Rin (trigger houses 2, 5, 9, 12)
        chart = {
            "house_status": {str(i): "Awake" for i in range(1, 13)},
            "lal_kitab_debts": [
                {
                    "debt_name": "Ancestral Debt (Pitra Rin)",
                    "active": True,
                    "trigger_houses": [2, 5, 9, 12]
                }
            ]
        }
        
        # Enriched planets with 10.0 strength in every house
        enriched = {
            f"P{i}": {"house": i, "strength_total": 10.0, "sleeping_status": "Awake"}
            for i in range(1, 13)
        }
        
        house_states = np.ones(12)
        multipliers = engine._compute_laplacian_multipliers(chart, enriched, house_states)
        
        # In a symmetric energetic system, Rin-affected houses should have lower multipliers
        # than their non-affected counterparts.
        # H1 (no Rin) vs H2 (Pitra Rin)
        assert multipliers[1] < multipliers[0], f"H2 ({multipliers[1]}) should be lower than H1 ({multipliers[0]}) due to Rin drain."
        # H4 (no Rin) vs H5 (Pitra Rin)
        assert multipliers[4] < multipliers[3], f"H5 ({multipliers[4]}) should be lower than H4 ({multipliers[3]}) due to Rin drain."

    def test_tag_fixed_saturates_magnitude(self):
        """Verify FIXED mutability (Pakka Ghar) saturates magnitude to 0.9."""
        engine = PhysicsEngine()
        
        # Sun in H1 (Pakka Ghar)
        enriched = {"Sun": {"house": 1, "strength_total": 5.0, "sleeping_status": "Awake"}}
        hit = RuleHit(
            rule_id="R1", domain="Career", description="Sun in 1", verdict="",
            magnitude=0.12, scoring_type="boost", primary_target_planets=["Sun"],
            target_houses=[1], success_weight=1.0, specificity=1, source_page=""
        )
        
        chart = {"house_status": {"1": "Awake"}, "lal_kitab_debts": []}
        
        engine.process(chart, [hit], enriched)
        
        assert getattr(hit, "mutability") == "FIXED"
        assert hit.magnitude == 0.9

    def test_mutability_priority(self):
        """Verify FIXED (Priority 0) overrides SLEEPING (Priority 4)."""
        engine = PhysicsEngine()
        
        # Sun in H1 (Pakka Ghar) but Sleeping
        enriched = {"Sun": {"house": 1, "strength_total": 5.0, "sleeping_status": "Sleeping Planet"}}
        hit = RuleHit(
            rule_id="R1", domain="Career", description="Sun in 1", verdict="",
            magnitude=0.12, scoring_type="boost", primary_target_planets=["Sun"],
            target_houses=[1], success_weight=1.0, specificity=1, source_page=""
        )
        
        chart = {"house_status": {"1": "Awake"}, "lal_kitab_debts": []}
        
        engine.process(chart, [hit], enriched)
        
        # FIXED priority 0 < SLEEPING priority 4
        assert getattr(hit, "mutability") == "FIXED"
        assert hit.magnitude == 0.9

    def test_laplacian_diffusion_spreads_energy(self):
        """Verify energy from a strong house (H1) spreads to house it aspects (H7)."""
        engine = PhysicsEngine()
        
        # Only H1 has a very strong planet
        enriched = {"Sun": {"house": 1, "strength_total": 100.0, "sleeping_status": "Awake"}}
        chart = {
            "house_status": {str(i): "Awake" for i in range(1, 13)},
            "lal_kitab_debts": []
        }
        
        # E_diffused = E + alpha * (A@E - D@E)
        # E = [100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # Sun in H1 aspects H7 (100% aspect).
        # Adjacency matrix A will have A[0, 6] = 1, A[6, 0] = 1.
        
        house_states = np.ones(12)
        multipliers = engine._compute_laplacian_multipliers(chart, enriched, house_states)
        
        # H7 should have received some energy from H1 via diffusion
        # (Assuming H7 has 0 base energy)
        assert multipliers[6] > 0.05
        # H1 should still be the max (normalized to 1.0)
        assert multipliers[0] == 1.0
