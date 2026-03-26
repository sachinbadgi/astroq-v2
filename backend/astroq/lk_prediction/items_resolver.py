"""
Planet + House article lookup for Lal Kitab remedies.
Data sourced from 'Items of planets.xlsx' (Sheets 1, 17, 19, 21, 23).
"""

import logging

logger = logging.getLogger(__name__)

class LKItemsResolver:
    """
    Resolves physical items and relatives associated with planets in specific houses.
    Used by RemedyEngine to suggest hints.
    """
    
    def __init__(self):
        # Canonical mappings from Sheets 1 and 19
        self._planet_house_items = {
            "Jupiter": {
                1: ["Goldsmith", "yellow colour", "male lion", "Sadhu on the move"],
                2: ["Cowshed", "hospitality", "worship", "wealth", "grams (pulse)", "Turmeric"],
                3: ["Durga poojan", "education", "worldly affairs"],
                4: ["Queen", "gold", "Rain"],
                5: ["Nose", "saffron"],
                6: ["Deer", "musk", "apples", "Chicken"],
                7: ["Books", "asthma", "frog", "vagabond Sadhu", "dirty air"],
                8: ["Rumour", "unemployment", "donation or Yagna of a Fakir"],
                9: ["Ancestral house", "place of worship", "gas", "Temple", "Mosque", "Gurudwara"],
                10: ["Dry peepal tree", "loss of gold", "end of education", "Sulphur"],
                11: ["Sulphur with nickel (gilt)"],
                12: ["Green peepal tree", "worldly affairs", "breath"]
            },
            "Sun": {
                1: ["Daytime", "Right side", "White salt", "Copper", "Gur"],
                2: ["Wheat", "Barely"],
                3: ["Progeny", "Nephews"],
                4: ["Son of father's sister", "Right eyeball"],
                5: ["Lone son", "Red faced monkey"],
                6: ["Wheatish colour", "Disease of feet"],
                7: ["Red cow"],
                8: ["Chariot", "Self generated fire"],
                9: ["Brown beer", "Sun after eclipse"],
                10: ["Brown Mongoose", "Brown buffalo", "stone gum"],
                11: ["Bright copper"],
                12: ["Brown ant", "Damaged brain"]
            },
            "Moon": {
                1: ["Left eyeball", "Heart", "Silver", "Milk"],
                2: ["Mother milk", "Rice", "White Horse"],
                3: ["Fiery Horse", "Shiva"],
                4: ["Well", "pool", "Spring", "Subsoil water", "peace"],
                5: ["Patridge (Chakor)", "Swallow wort", "Milk"],
                6: ["Male rabbit", "Travel"],
                7: ["Agriculture land of ice"],
                8: ["Sea", "Epilepsy", "Chicken hearted"],
                9: ["Ancestral property", "Sea"],
                10: ["Night time", "Bitter water", "Foundation", "Bitter opium"],
                11: ["Silky Pearl-(Milky)", "Bloody well", "Floating clouds"],
                12: ["White cat", "Rain water", "Rain stone", "Camphor"]
            },
            "Mars": {
                1: ["Teeth 32/31", "Grainstore", "Aniseed"],
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
                2: ["White cow", "Female Elephant", "Ghee", "Ginger", "Camphor"],
                3: ["Marriage", "contended wife"],
                4: ["Curd", "Four wheeled", "Birds"],
                5: ["Brick", "Brass utensil"],
                6: ["Sparrows", "Eunuch"],
                7: ["White cow", "Barley (white)"],
                8: ["Sweet Potato", "Carrot"],
                9: ["Curds colour"],
                10: ["Sweet", "Cotton"],
                11: ["Cotton", "white colour", "Pearl", "Curd"],
                12: ["Kamdhenu cow", "Lakshmi's foot", "Family", "wife comfort"]
            },
            "Mercury": {
                1: ["Tongue", "Skull"],
                2: ["Kidney Beans", "Sister-in-law", "Musical instruments", "peas"],
                3: ["Brother's daughter", "Bat", "Cactus", "Termite"],
                4: ["Parrot", "Soldering metal", "Vertical egg", "Father's sister"],
                5: ["Bamboo", "Milch goat", "Grand daughter"],
                6: ["Fruit", "Daughter", "Grand daughter", "Vertical egg"],
                7: ["Green grass", "Cow without tail", "Female parrot"],
                8: ["Lying egg", "Dead body", "Flower", "Sister"],
                9: ["Ghosts", "Bat", "Green colour forest", "Lisping"],
                10: ["Teeth", "Dry grass", "Liquor", "Stairs", "Musical Drums", "Heeng"],
                11: ["Parrot", "Seashell", "Alum", "Diamond"],
                12: ["Egg", "Toys", "Dirty egg"]
            },
            "Saturn": {
                1: ["Crow", "Black Salt", "Acacia (Kikkar)", "Insects"],
                2: ["Full Black pulse", "Black paper", "Black grams", "Sandalwood"],
                3: ["Butte Frondosa (Dhaak Tree)", "Precious wood", "Mulberry"],
                4: ["Black insects", "oil", "Marble", "Wood of Diyar and pine"],
                5: ["Black antimony", "Stupid son"],
                6: ["Crow", "Kite", "Plum", "Coal", "Stone", "Cotton seeds"],
                7: ["Black cow", "White antimony", "Eyes", "Condiments"],
                8: ["Scorpion", "Walls without roof", "Temple (Body)"],
                9: ["Old wood", "Swallow-Wort-(Aak)", "Seesam Tree"],
                10: ["Crocodile", "Snake", "Oil", "Soap", "Laundry"],
                11: ["Iron", "Steel", "Tin"],
                12: ["Artificial copper", "Fish", "Almonds", "Baldness"]
            },
            "Rahu": {
                1: ["Chin", "Mother's parents"],
                2: ["Soil of elephant feet", "Mustard", "Raw smoke"],
                3: ["Lower position of tongue", "Elephant"],
                4: ["Dream time", "Coriander"],
                5: ["Roof"],
                6: ["Pitch black dog"],
                7: ["Coconut"],
                8: ["Swing", "disease", "Smoke of Chimney", "Agate"],
                9: ["Watch", "Door step", "Blue colour"],
                10: ["Latrine", "Outlet for dirty water", "Roasting furnace"],
                11: ["Blue sapphire", "Aluminium", "Zinc", "copper Sulphate"],
                12: ["Elephant", "Sea Tendua", "Raw Coal"]
            },
            "Ketu": {
                1: ["Leg", "Maternal House"],
                2: ["Tamarind", "Sesame"],
                3: ["Spinal chord", "Boils"],
                4: ["Hearing", "Ears"],
                5: ["Urinal"],
                6: ["Male sparrow", "Rabbit", "Onion", "Bedstead", "Garlic"],
                7: ["Second son", "Donkey", "Pig"],
                8: ["Ear", "Hearing power", "Deceiving nature"],
                9: ["Two coloured dog"],
                10: ["Rat", "Mouse"],
                11: ["Twin coloured stone (black and white)"],
                12: ["Lizard", "Adopted Son", "bed", "Banana"]
            }
        }
        
        # Sheet 21: Relatives
        self._planet_relatives = {
            "Jupiter": {1: "Father/Grandfather", 2: "In-laws of woman", 3: "Head of Family", 4: "Magnanimous father"},
            "Sun": {1: "Self", 2: "Religious minister", 3: "Aggressive friend", 9: "Kind friend"},
            "Moon": {1: "Queen", 4: "Mother or her sister", 6: "Mother's mother"},
            "Venus": {1: "Wife/Husband", 7: "Life long spouse"},
            "Mars": {1: "Brother", 2: "Elder brother", 7: "Real brother"},
            "Mercury": {1: "Eldest daughter", 3: "Elder sister", 6: "Own daughter"},
            "Saturn": {1: "Officer", 7: "Helpful person", 10: "Honorable paternal uncle"},
            "Rahu": {2: "Father-in-law", 3: "Sincere friend", 4: "Maternal uncle"},
            "Ketu": {1: "Lone son", 3: "Brother's son", 7: "Second son", 9: "Loyal son"}
        }

    def get_planet_items(self, planet: str, house: int) -> list[str]:
        """Returns physical items associated with planet in house."""
        p_map = self._planet_house_items.get(planet, {})
        items = p_map.get(house, [])
        if not items:
            return ["Associated items (see physical Lal Kitab)"]
        return items

    def get_planetary_relatives(self, planet: str, house: int) -> list[str]:
        """Returns relatives associated with planet in house."""
        p_map = self._planet_relatives.get(planet, {})
        relative = p_map.get(house)
        return [relative] if relative else []
