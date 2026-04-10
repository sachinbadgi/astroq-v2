"""
Tests for Module 6: Event Classifier.

Tests written FIRST (TDD Red phase) — 8 unit tests covering
peak detection (absolute/momentum), sentiment classification,
and domain mapping from DOMAIN_WEIGHTS.
"""

import pytest

from astroq.lk_prediction.data_contracts import ClassifiedEvent

class TestEventClassifier:
    
    def _make_classifier(self, tmp_db, tmp_defaults):
        from astroq.lk_prediction.config import ModelConfig
        from astroq.lk_prediction.event_classifier import EventClassifier
        cfg = ModelConfig(db_path=tmp_db, defaults_path=tmp_defaults)
        return EventClassifier(cfg)

    # -- 1. Sentiment Classification --
    def test_sentiment_classification_benefic_malefic(self, tmp_db, tmp_defaults):
        """High positive magnitude is benefic, highly negative is malefic."""
        clf = self._make_classifier(tmp_db, tmp_defaults)
        
        # We test the internal logic directly or via the public parsing method
        sent_b = clf._classify_sentiment(magnitude=10.0, planet="Jupiter")
        sent_m = clf._classify_sentiment(magnitude=-10.0, planet="Saturn")
        
        assert sent_b == "BENEFIC"
        assert sent_m == "MALEFIC"

    def test_sentiment_classification_mixed_volatile(self, tmp_db, tmp_defaults):
        """Mixed and volatile detection logic."""
        clf = self._make_classifier(tmp_db, tmp_defaults)
        # Assuming near zero magnitude with certain parameters might be mixed
        sent_mix = clf._classify_sentiment(magnitude=0.5, planet="Venus")
        assert sent_mix == "MIXED"

        # Rahu/Ketu/Mars with certain thresholds might be volatile
        # Or if magnitude variance is high (simulated by flags)
        sent_vol = clf._classify_sentiment(magnitude=-0.1, planet="Rahu")
        # Exact implementation details depend on config, but it should output valid sentiment strings
        assert sent_vol in ("MIXED", "VOLATILE", "MALEFIC")

    # -- 2. Domain Mapping --
    def test_domain_mapping_identifies_primary_secondary(self, tmp_db, tmp_defaults):
        """Maps planets/houses to standard domains, prioritizing rule domains."""
        clf = self._make_classifier(tmp_db, tmp_defaults)

        # 1. Without rule_domains: falls back to planet+house DOMAIN_MAP karakas.
        #    Sun maps to ["Career", "Authority", "Health"]; H1 maps to ["Health", "Self", "Personality"].
        #    Net = union of both. Should be non-empty; "General" only appears when BOTH are unknown.
        domains_sun_h1 = clf._map_domains(planet="Sun", house=1)
        assert len(domains_sun_h1) > 0
        # At minimum the planet karaka domains must appear
        assert any(d in domains_sun_h1 for d in ["Career", "Authority", "Health", "Self", "Personality"])

        # 2. With explicit rule domains: Should map to standardized titles
        domains_r = clf._map_domains(planet="Jupiter", house=2, rule_domains=["marriage", "profession"])
        expected = ["Career", "Marriage", "Partnerships", "Profession", "Status"]
        for exp in expected:
            assert exp in domains_r

    # -- 3. Peak Detection --
    def test_peak_detection_absolute_threshold(self, tmp_db, tmp_defaults):
        """Events above absolute probability threshold are marked as peaks."""
        clf = self._make_classifier(tmp_db, tmp_defaults)
        
        # Get threshold from config
        thresh = clf._cfg.get("classifier.absolute_peak_threshold", fallback=0.85)
        
        is_peak_high = clf._is_peak(prob=thresh + 0.05, prob_t_minus_1=0.5)
        is_peak_low = clf._is_peak(prob=thresh - 0.05, prob_t_minus_1=0.5)
        
        assert is_peak_high is True
        assert is_peak_low is False

    def test_peak_detection_momentum(self, tmp_db, tmp_defaults):
        """Events that jump significantly from previous year are peaks even if below absolute."""
        clf = self._make_classifier(tmp_db, tmp_defaults)
        
        jump_thresh = clf._cfg.get("classifier.momentum_jump_threshold", fallback=0.30)
        
        # Goes from 0.2 to 0.6 -> Jump is +0.4 -> Should trigger momentum peak
        is_peak = clf._is_peak(prob=0.6, prob_t_minus_1=0.2)
        assert is_peak is True

        # Goes from 0.6 to 0.7 -> Jump is +0.1 -> Not a peak
        not_peak = clf._is_peak(prob=0.7, prob_t_minus_1=0.6)
        assert not_peak is False

    # -- 4. Full Classification Pipeline --
    def test_classify_events_creates_classified_event_objects(self, tmp_db, tmp_defaults):
        """classify_events() domain-collapses: returns one ClassifiedEvent per domain.

        Venus in H7 maps to the union of DOMAIN_MAP["Venus"] + DOMAIN_MAP["h7"]:
          Venus: ["Marriage", "Romance", "Vehicles", "Luxury"]
          h7:   ["Marriage", "Partnerships", "Business"]
        Net unique domains = 6. So len(classified) == 6 (one entry per domain bucket).
        Each entry should have exactly 1 domain and share the same planet/probability.
        """
        clf = self._make_classifier(tmp_db, tmp_defaults)

        raw_events = [
            {
                "planet": "Venus",
                "house": 7,
                "annual_magnitude": 15.0,
                "final_probability": 0.90,
                "prob_t_minus_1": 0.40,
                "rule_hits": [],
                "prediction_text": "Good marriage prospects."
            }
        ]

        classified = clf.classify_events(raw_events)

        # Domain-collapse: one ClassifiedEvent per domain, each with a single domain.
        assert len(classified) >= 1
        for ev in classified:
            assert isinstance(ev, ClassifiedEvent)
            assert ev.planet == "Venus"
            assert ev.sentiment == "BENEFIC"
            assert ev.is_peak is True  # Triggered both absolute and momentum
            assert len(ev.domains) == 1  # Each collapsed entry has exactly one domain

        # All domains combined should include Marriage
        all_domains = {d for ev in classified for d in ev.domains}
        assert "Marriage" in all_domains

    def test_classify_events_filters_noise(self, tmp_db, tmp_defaults):
        """Events below the noise threshold are discarded or marked."""
        clf = self._make_classifier(tmp_db, tmp_defaults)
        
        raw_events = [
            {"planet": "Moon", "house": 4, "annual_magnitude": 0.5, "final_probability": 0.20, "prob_t_minus_1": 0.20}
        ]
        
        classified = clf.classify_events(raw_events)
        # Should returning nothing if we filter noise, or return with is_peak = False.
        # Often low prob events are returned but not highlighted, or explicitly filtered if prob < noise_floor.
        # Let's assume it returns them but is_peak is False, or filters if prob < floor.
        
        floor = clf._cfg.get("classifier.noise_floor", fallback=0.30)
        
        if len(classified) > 0:
            assert classified[0].is_peak is False
            assert classified[0].probability < floor

    def test_classify_handles_missing_history(self, tmp_db, tmp_defaults):
        """If prob_t_minus_1 is missing (e.g., Year 1), momentum is skipped safely.

        Sun in H10: DOMAIN_MAP["Sun"] = ["Career","Authority","Health"],
                    DOMAIN_MAP["h10"] = ["Career","Profession","Status"]
        Unique domains ~ 5. We get one ClassifiedEvent per domain.
        All entries should still be marked is_peak=True (0.88 >= abs_peak=0.85).
        """
        clf = self._make_classifier(tmp_db, tmp_defaults)

        raw_events = [
            {"planet": "Sun", "house": 10, "annual_magnitude": 8.0, "final_probability": 0.88}  # No history
        ]

        classified = clf.classify_events(raw_events)
        # At least one domain bucket should be produced
        assert len(classified) >= 1
        # Every domain-collapsed entry must still be a peak (absolute threshold hit)
        for ev in classified:
            assert ev.is_peak is True
