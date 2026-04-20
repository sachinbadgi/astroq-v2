"""
Module 7: Prediction Translator

Translates raw RuleHit data and planetary states into human-readable predictions,
relatives, and physical articles for remedies.
"""

from typing import List, Dict, Any, Tuple
from astroq.lk_prediction.data_contracts import RuleHit, LKPrediction
from astroq.lk_prediction.config import ModelConfig

PLANET_HOUSE_ITEMS = {
    "Jupiter": {
        1: ["Goldsmith", "yellow colour", "male lion", "Sadhu on the move"],
        2: ["Cowshed", "Turmeric", "wealth"],
        3: ["Durga poojan", "education"],
        4: ["Queen", "gold", "Rain"],
        5: ["Nose", "saffron"],
        6: ["Deer", "musk", "apples"],
        7: ["Books", "frog", "vagabond Sadhu"],
        8: ["Rumour", "unemployment", "Yagna"],
        9: ["Ancestral house", "Temple", "Mosque", "Gurudwara"],
        10: ["Dry peepal tree", "Sulphur"],
        11: ["Sulphur with nickel"],
        12: ["Green peepal tree", "breath"]
    },
    "Sun": {
        1: ["White salt", "Copper", "Gur"],
        2: ["Wheat", "Barely"],
        3: ["Progeny", "Nephews"],
        4: ["Right eyeball"],
        5: ["Lone son", "Red faced monkey"],
        6: ["Wheatish colour"],
        7: ["Red cow"],
        8: ["Chariot", "Self generated fire"],
        9: ["Brown beer"],
        10: ["Brown Mongoose", "stone gum"],
        11: ["Bright copper"],
        12: ["Brown ant"]
    },
    "Moon": {
        1: ["Silver", "Milk", "Heart"],
        2: ["Mother milk", "Rice", "White Horse"],
        3: ["Fiery Horse", "Shiva"],
        4: ["Well", "pool", "Spring"],
        5: ["Milk", "Swallow wort"],
        6: ["Male rabbit", "Travel"],
        7: ["Agriculture land of ice"],
        8: ["Sea", "Epilepsy"],
        9: ["Ancestral property", "Sea"],
        10: ["Night time", "Bitter water", "Opium"],
        11: ["Silky Pearl", "Floating clouds"],
        12: ["White cat", "Rain water", "Camphor"]
    },
    "Mars": {
        1: ["Teeth", "Aniseed"],
        2: ["Leopard", "Deer"],
        3: ["Stomach", "Lips", "Chest"],
        4: ["Deer skin", "Sword", "Dhak"],
        5: ["Brother", "Neem tree"],
        6: ["Partridge", "Musk Rat"],
        7: ["Lentil", "Thymol"],
        8: ["Body without arms"],
        9: ["Bloody red colour"],
        10: ["Honey sweet", "Food Sugar"],
        11: ["Red colour of Vermilion"],
        12: ["Driver of loud elephant"]
    },
    "Venus": {
        1: ["Other woman"],
        2: ["White cow", "Ghee", "Ginger", "Camphor"],
        3: ["Marriage", "contended wife"],
        4: ["Curd", "Four wheeled", "Birds"],
        5: ["Brick", "Brass utensil"],
        6: ["Sparrows", "Eunuch"],
        7: ["White cow", "Barley (white)"],
        8: ["Sweet Potato", "Carrot"],
        9: ["Curds colour"],
        10: ["Sweet", "Cotton"],
        11: ["Cotton", "Pearl", "Curd"],
        12: ["Kamdhenu cow", "Lakshmi's foot", "Family"]
    },
    "Mercury": {
        1: ["Tongue", "Skull"],
        2: ["Kidney Beans", "peas"],
        3: ["Bat", "Cactus", "Termite"],
        4: ["Parrot", "Soldering metal"],
        5: ["Bamboo", "Milch goat"],
        6: ["Fruit", "Daughter"],
        7: ["Green grass", "Cow without tail"],
        8: ["Flower", "Sister"],
        9: ["Ghosts", "Bat", "Green colour forest"],
        10: ["Teeth", "Dry grass", "Liquor", "Stairs"],
        11: ["Parrot", "Seashell", "Alum", "Diamond"],
        12: ["Egg", "Toys"]
    },
    "Saturn": {
        1: ["Crow", "Black Salt", "Acacia"],
        2: ["Full Black pulse", "Black paper", "Sandalwood"],
        3: ["Precious wood", "Mulberry"],
        4: ["Black insects", "oil", "Marble"],
        5: ["Black antimony"],
        6: ["Crow", "Plum", "Coal", "Stone"],
        7: ["Black cow", "White antimony", "Eyes"],
        8: ["Scorpion", "Walls without roof"],
        9: ["Old wood", "Seesam Tree"],
        10: ["Crocodile", "Snake", "Oil", "Soap"],
        11: ["Iron", "Steel", "Tin"],
        12: ["Artificial copper", "Fish", "Almonds"]
    },
    "Rahu": {
        1: ["Chin", "Mother's parents"],
        2: ["Mustard", "Raw smoke"],
        3: ["Elephant"],
        4: ["Dream time", "Coriander"],
        5: ["Roof"],
        6: ["Pitch black dog"],
        7: ["Coconut"],
        8: ["Agate", "Smoke of Chimney"],
        9: ["Watch", "Blue colour"],
        10: ["Latrine", "Outlet for dirty water"],
        11: ["Blue sapphire", "Aluminium", "Zinc"],
        12: ["Elephant", "Raw Coal"]
    },
    "Ketu": {
        1: ["Leg", "Maternal House"],
        2: ["Tamarind", "Sesame"],
        3: ["Spinal chord", "Boils"],
        4: ["Hearing", "Ears"],
        5: ["Urinal"],
        6: ["Male sparrow", "Rabbit", "Onion"],
        7: ["Second son", "Donkey", "Pig"],
        8: ["Ear", "Hearing power"],
        9: ["Two coloured dog"],
        10: ["Rat", "Mouse"],
        11: ["Twin coloured stone"],
        12: ["Lizard", "Adopted Son", "bed"]
    }
}

PLANET_RELATIVES = {
    "Jupiter": {1: "Father/Grandfather", 2: "In-laws"},
    "Sun": {1: "Self", 2: "Religious minister", 3: "Aggressive friend"},
    "Moon": {1: "Queen", 4: "Mother", 6: "Mother's mother"},
    "Venus": {1: "Wife/Husband", 7: "Life long spouse"},
    "Mars": {1: "Brother", 2: "Elder brother", 7: "Real brother"},
    "Mercury": {1: "Daughter", 3: "Sister", 6: "Own daughter"},
    "Saturn": {1: "Officer", 7: "Helpful person", 10: "Paternal uncle"},
    "Rahu": {2: "Father-in-law", 3: "Sincere friend", 4: "Maternal uncle"},
    "Ketu": {1: "Lone son", 3: "Brother's son", 7: "Second son"}
}

class PredictionTranslator:
    """Consolidated Interpretation layer for raw RuleHits."""

    def __init__(self, config: ModelConfig):
        self._cfg = config

    def translate(self, rule_hits: List[RuleHit], age: int = 0) -> List[LKPrediction]:
        predictions = []
        for hit in rule_hits:
            p = LKPrediction(
                domain=hit.domain,
                event_type=hit.rule_id,
                prediction_text=f"{hit.description}: {hit.verdict}",
                polarity="BENEFIC" if hit.magnitude >= 0 else "MALEFIC",
                peak_age=age,
                magnitude=hit.magnitude,
                source_planets=hit.primary_target_planets,
                source_houses=hit.target_houses,
                source_rules=[hit.rule_id]
            )
            
            # Enrich with relatives and items
            for planet in hit.primary_target_planets:
                for house in hit.target_houses:
                    p.affected_people.extend(PLANET_RELATIVES.get(planet, {}).get(house, "").split("/"))
                    p.affected_items.extend(PLANET_HOUSE_ITEMS.get(planet, {}).get(house, []))
            
            p.affected_people = sorted(list(set([x for x in p.affected_people if x])))
            
            # Remedy generation (canonical)
            if p.polarity == "MALEFIC":
                p.remedy_applicable = True
                p.remedy_hints = self._generate_simple_hints(hit)
                
            predictions.append(p)
        return predictions

    def _generate_simple_hints(self, hit: RuleHit) -> List[str]:
        """Generate first-pass remedy hints based on planet and house articles."""
        hints = []
        for planet in hit.primary_target_planets:
            for house in hit.target_houses:
                articles = PLANET_HOUSE_ITEMS.get(planet, {}).get(house, [])
                if articles:
                    hints.append(f"Keep/Donate {articles[0]} related to {planet} in House {house}.")
        return hints
