import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.lse_researcher import ResearcherAgent
from astroq.lk_prediction.data_contracts import ChartData, GapEntry

def test_rationales():
    researcher = ResearcherAgent()
    
    # 1. Test Progeny: Saturn in H5
    chart_h5_sat = {
        "planets_in_houses": {
            "Saturn": {"house": 5},
            "Jupiter": {"house": 1}
        },
        "house_status": {"5": "Occupied"}
    }
    gap_progeny = {
        "life_event": {"age": 30, "domain": "progeny"},
        "predicted_peak_age": 28,
        "source_planets": ["Saturn"]
    }
    rationale = researcher.find_astrological_rationale(gap_progeny, chart_h5_sat)
    print(f"Test Progeny (Saturn H5): {rationale['condition_name'] if rationale else 'FAILED'}")

    # 2. Test Litigation: Moon H12 + Ketu H1
    chart_litigation = {
        "planets_in_houses": {
            "Moon": {"house": 12},
            "Ketu": {"house": 1}
        }
    }
    gap_litigation = {
        "life_event": {"age": 40, "domain": "litigation"},
        "predicted_peak_age": 35
    }
    rationale = researcher.find_astrological_rationale(gap_litigation, chart_litigation)
    print(f"Test Litigation (Moon H12 + Ketu H1): {rationale['condition_name'] if rationale else 'FAILED'}")

    # 3. Test Wealth: Rahu in H9 (Age 42+)
    chart_rah_h9 = {
        "planets_in_houses": {
            "Rahu": {"house": 9}
        }
    }
    gap_wealth = {
        "life_event": {"age": 45, "domain": "wealth"},
        "predicted_peak_age": 42
    }
    rationale = researcher.find_astrological_rationale(gap_wealth, chart_rah_h9)
    print(f"Test Wealth (Rahu H9): {rationale['condition_name'] if rationale else 'FAILED'}")

    # 4. Test Wealth: Empty H2 & H4
    chart_empty = {
        "planets_in_houses": {"Jupiter": {"house": 1}},
        "house_status": {"2": "Sleeping House", "4": "Sleeping House"}
    }
    gap_wealth_empty = {
        "life_event": {"age": 50, "domain": "wealth"},
        "predicted_peak_age": 45
    }
    rationale = researcher.find_astrological_rationale(gap_wealth_empty, chart_empty)
    print(f"Test Wealth (Empty H2/H4): {rationale['condition_name'] if rationale else 'FAILED'}")

if __name__ == "__main__":
    test_rationales()
