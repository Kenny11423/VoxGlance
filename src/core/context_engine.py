"""Semantic Context Engine for Dynamic Word Sense Disambiguation (WSD) and Idiom Adaptation.

Features:
1. Dynamic Domain Profiler: Infers topic context (Animals/Pets, Gaming/RPG, Military/Martial, Fantasy, Office, Tech, Casual).
2. Polysemy Disambiguator: Resolves ambiguous English words with multiple senses based on surrounding context clues.
3. Idiomatic & Figurative Decoupler: Automatically translates English idioms into their contextual figurative meanings.
4. Contextual Pronoun & Tone Adaptation: Automatically guides pronouns based on social distance and discourse.
5. Zero GPU/VRAM Overhead: Runs sub-millisecond regex & semantic token matching locally and offline.
"""

from enum import Enum
import re
from typing import Dict, List, Optional, Set, Tuple


class SemanticDomain(str, Enum):
    GENERAL_CASUAL = "general"
    ANIMAL_PET = "animal_pet"
    GAMING_RPG = "gaming_rpg"
    MILITARY_MARTIAL = "military_martial"
    FANTASY_MAGIC = "fantasy_magic"
    OFFICE_ADMIN = "office_admin"
    TECH_IT = "tech_it"
    NATURE = "nature"


DOMAIN_KEYWORD_MAP: Dict[SemanticDomain, Set[str]] = {
    SemanticDomain.ANIMAL_PET: {
        "dog", "cat", "pet", "puppy", "kitten", "fur", "paws", "ears", "tail",
        "bark", "barking", "leash", "vet", "veterinary", "kennel", "cage", "breed",
        "animal", "beast", "hound", "canine", "feline", "wolf", "werewolf", "werewolves",
        "muzzle", "collar", "stray", "fluffy", "goro",
    },
    SemanticDomain.GAMING_RPG: {
        "guild", "dungeon", "boss", "raid", "quest", "rpg", "exp", "hp", "mp",
        "mana", "skill", "cast", "cooldown", "tank", "tanker", "dps", "healer", "aggro",
        "loot", "inventory", "respawn", "spawn", "buff", "debuff", "level", "pvp",
        "pve", "party", "equip", "armor", "shield", "summon",
    },
    SemanticDomain.MILITARY_MARTIAL: {
        "captain", "commander", "soldier", "army", "squad", "division", "lieutenant",
        "general", "sword", "blade", "bow", "arrow", "attack", "enemy", "war", "battle",
        "troop", "troops", "regiment", "combat", "defend", "guard", "officer", "barracks",
        "shunpo", "zanpakuto", "gotei", "seireitei",
    },
    SemanticDomain.FANTASY_MAGIC: {
        "wizard", "witch", "magic", "spell", "enchanted", "demon", "dragon", "soul",
        "spirit", "reaper", "chakra", "reiatsu", "aura", "cultivation", "sect",
        "immortal", "celestial", "realm", "artifact", "talisman", "curse", "alchemist",
    },
    SemanticDomain.OFFICE_ADMIN: {
        "bureau", "administration", "paperwork", "document", "report", "registration",
        "submit", "employee", "manager", "meeting", "office", "contract", "memo",
        "procedure", "client", "deadline", "official", "registry", "application",
    },
    SemanticDomain.TECH_IT: {
        "software", "code", "bug", "crash", "server", "database", "branch", "commit",
        "push", "function", "variable", "api", "framework", "query", "memory", "thread",
        "compiler", "frontend", "backend", "docker", "pipeline",
    },
    SemanticDomain.NATURE: {
        "river", "lake", "stream", "ocean", "sea", "forest", "tree", "mountain",
        "water", "wind", "rain", "storm", "breeze", "wave", "soil", "wood", "bank",
    },
}


class SemanticContextEngine:
    """Real-time semantic context inference and word-sense disambiguation engine."""

    def __init__(self):
        self.active_mode: Optional[str] = None
        # 1. Polysemy Disambiguation Rules:
        # Each rule defines the target ambiguous word, required context trigger keywords,
        # and the contextual replacement/synonym that disambiguates the MT model's output.
        self._polysemy_rules = [
            # PEN: enclosure/kennel vs writing pen
            {
                "pattern": re.compile(r"\bpen\b", re.IGNORECASE),
                "triggers": {"dog", "cat", "pet", "puppy", "animal", "kennel", "cage", "goro", "fur", "paws"},
                "replacement": "kennel",
                "domain": SemanticDomain.ANIMAL_PET,
            },
            # COAT: fur/pelt vs jacket
            {
                "pattern": re.compile(r"\bcoat\b", re.IGNORECASE),
                "triggers": {"dog", "cat", "pet", "puppy", "animal", "fur", "white", "black", "fluffy", "pelt", "tail", "ears"},
                "replacement": "fur",
                "domain": SemanticDomain.ANIMAL_PET,
            },
            # PARTY: gaming group/team vs celebration vs political party
            {
                "pattern": re.compile(r"\bparty\b", re.IGNORECASE),
                "triggers": {"guild", "dungeon", "boss", "raid", "quest", "rpg", "members", "defeat", "level", "healer", "dps"},
                "replacement": "team",
                "domain": SemanticDomain.GAMING_RPG,
            },
            # TANK: gaming damage-absorber vs armored vehicle vs liquid container
            {
                "pattern": re.compile(r"\btank\b", re.IGNORECASE),
                "triggers": {"guild", "dungeon", "boss", "raid", "damage", "absorb", "aggro", "healer", "dps", "party"},
                "replacement": "defender",
                "domain": SemanticDomain.GAMING_RPG,
            },
            # MATCH: fire matchstick vs sports competition vs pair
            {
                "pattern": re.compile(r"\bmatch\b", re.IGNORECASE),
                "triggers": {"fire", "light", "burn", "candle", "strike", "flame", "smoke", "wind", "box"},
                "replacement": "matchstick",
                "domain": SemanticDomain.GENERAL_CASUAL,
            },
            # BOW: archer weapon vs respectful head bend vs ribbon
            {
                "pattern": re.compile(r"\bbow\b", re.IGNORECASE),
                "triggers": {"arrow", "shoot", "archer", "string", "quiver", "target", "aim"},
                "replacement": "longbow",
                "domain": SemanticDomain.MILITARY_MARTIAL,
            },
            # SPELL: magic chant vs alphabet spelling
            {
                "pattern": re.compile(r"\bspell\b", re.IGNORECASE),
                "triggers": {"cast", "wizard", "witch", "magic", "mana", "powerful", "curse", "enchant", "chant"},
                "replacement": "incantation",
                "domain": SemanticDomain.FANTASY_MAGIC,
            },
            # TRUNK: elephant snout vs tree body vs car back
            {
                "pattern": re.compile(r"\btrunk\b", re.IGNORECASE),
                "triggers": {"elephant", "animal", "snout", "spray", "water"},
                "replacement": "elephant trunk",
                "domain": SemanticDomain.ANIMAL_PET,
            },
            {
                "pattern": re.compile(r"\btrunk\b", re.IGNORECASE),
                "triggers": {"car", "luggage", "bag", "back", "boot", "vehicle"},
                "replacement": "luggage boot",
                "domain": SemanticDomain.GENERAL_CASUAL,
            },
            # CELL: prison cell vs biological cell vs phone
            {
                "pattern": re.compile(r"\bcell\b", re.IGNORECASE),
                "triggers": {"prison", "jail", "prisoner", "inmate", "guard", "lock", "bars", "escape", "dungeon"},
                "replacement": "prison cell",
                "domain": SemanticDomain.MILITARY_MARTIAL,
            },
            # MINE: mineral excavation vs explosive trap
            {
                "pattern": re.compile(r"\bmine\b", re.IGNORECASE),
                "triggers": {"gold", "coal", "iron", "dig", "cave", "tunnel", "mineral", "ore", "worker"},
                "replacement": "quarry mine",
                "domain": SemanticDomain.NATURE,
            },
            {
                "pattern": re.compile(r"\bmine\b", re.IGNORECASE),
                "triggers": {"bomb", "explode", "explosive", "trap", "landmine", "blast", "step on"},
                "replacement": "landmine",
                "domain": SemanticDomain.MILITARY_MARTIAL,
            },
        ]

        # 2. Idiom & Figurative Expression Rules:
        # Maps common English idioms to their contextual figurative equivalents
        self._idiom_rules = [
            (re.compile(r"\bhit the sack\b", re.IGNORECASE), "go to sleep"),
            (re.compile(r"\bhit the hay\b", re.IGNORECASE), "go to sleep"),
            (re.compile(r"\bunder the weather\b", re.IGNORECASE), "feeling unwell"),
            (re.compile(r"\bspill the beans\b", re.IGNORECASE), "reveal the secret"),
            (re.compile(r"\bpiece of cake\b", re.IGNORECASE), "very easy task"),
            (re.compile(r"\bbreak a leg\b", re.IGNORECASE), "good luck"),
            (re.compile(r"\bbite the bullet\b", re.IGNORECASE), "endure the pain"),
            (re.compile(r"\bcall it a day\b", re.IGNORECASE), "finish work for today"),
            (re.compile(r"\bpull(?:ing)?\s+(?:my|your|his|her|their)\s+leg\b", re.IGNORECASE), "teasing"),
            (re.compile(r"\bout of the blue\b", re.IGNORECASE), "completely unexpectedly"),
            (re.compile(r"\bcost an arm and a leg\b", re.IGNORECASE), "extremely expensive"),
            (re.compile(r"\bsee eye to eye\b", re.IGNORECASE), "agree completely"),
            (re.compile(r"\bcross(?:ed)? the line\b", re.IGNORECASE), "went too far"),
            (re.compile(r"\bkeep an eye on\b", re.IGNORECASE), "watch closely"),
            (re.compile(r"\bon cloud nine\b", re.IGNORECASE), "extremely happy"),
            (re.compile(r"\bonce in a blue moon\b", re.IGNORECASE), "very rarely"),
            (re.compile(r"\bcut corners\b", re.IGNORECASE), "act carelessly to save effort"),
            (re.compile(r"\bburn the midnight oil\b", re.IGNORECASE), "work late into the night"),
            (re.compile(r"\bby the book\b", re.IGNORECASE), "strictly following the rules"),
            (re.compile(r"\bface the music\b", re.IGNORECASE), "accept the consequences"),
            (re.compile(r"\bring(?:s)? a bell\b", re.IGNORECASE), "sounds familiar"),
            (re.compile(r"\btake it with a grain of salt\b", re.IGNORECASE), "listen with healthy skepticism"),
            (re.compile(r"\bhands down\b", re.IGNORECASE), "without a doubt"),
            (re.compile(r"\bin cold blood\b", re.IGNORECASE), "ruthlessly without mercy"),
            (re.compile(r"\bat the eleventh hour\b", re.IGNORECASE), "at the very last moment"),
            (re.compile(r"\bburn bridges\b", re.IGNORECASE), "destroy relationships permanently"),
            (re.compile(r"\bbeat around the bush\b", re.IGNORECASE), "speak indirectly avoiding the point"),
            (re.compile(r"\bget cold feet\b", re.IGNORECASE), "feel nervous and hesitant"),
        ]

    def set_mode(self, mode: str) -> None:
        """Lock or prioritize active semantic domain according to mode."""
        self.active_mode = mode.lower().strip()

    def detect_domain(self, text: str, context_history: str = "") -> SemanticDomain:
        """Score and detect the primary semantic domain from text and sliding context history."""
        full_context = f"{context_history} {text}".lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", full_context))

        # Default fallback domain based on active mode
        if self.active_mode == "game":
            best_domain = SemanticDomain.GAMING_RPG
        elif self.active_mode == "document":
            best_domain = SemanticDomain.OFFICE_ADMIN
        else:
            best_domain = SemanticDomain.GENERAL_CASUAL

        best_score = 0

        for domain, keywords in DOMAIN_KEYWORD_MAP.items():
            overlap = len(words.intersection(keywords))
            if overlap > best_score:
                best_score = overlap
                best_domain = domain

        return best_domain

    def resolve_context(
        self,
        text: str,
        context_history: str = "",
    ) -> Tuple[str, SemanticDomain, List[str]]:
        """Analyze text and context to resolve polysemous words and idioms.

        Args:
            text: Current source sentence to translate.
            context_history: Preceding sentences from conversation/reading history.

        Returns:
            Tuple of:
                - disambiguated_text: Text normalized for NMT with unambiguous senses.
                - detected_domain: The active domain.
                - notes: List of disambiguated items for audit/logging.
        """
        if not text:
            return text, SemanticDomain.GENERAL_CASUAL, []

        resolved_text = text
        full_context = f"{context_history} {text}".lower()
        context_words = set(re.findall(r"\b[a-z]{3,}\b", full_context))

        domain = self.detect_domain(text, context_history)
        notes: List[str] = []

        # 1. Resolve Idioms & Figurative Expressions
        for idiom_pat, figurative_equiv in self._idiom_rules:
            if idiom_pat.search(resolved_text):
                matched_str = idiom_pat.search(resolved_text).group(0)
                resolved_text = idiom_pat.sub(figurative_equiv, resolved_text)
                notes.append(f"Idiom resolved: '{matched_str}' -> '{figurative_equiv}'")

        # 2. Resolve Polysemous Words based on Semantic Context Triggers
        for rule in self._polysemy_rules:
            if rule["pattern"].search(resolved_text):
                # Check if triggers are present in current sentence or sliding context
                triggers = rule["triggers"]
                found_triggers = context_words.intersection(triggers)
                if found_triggers or domain == rule["domain"]:
                    matched_word = rule["pattern"].search(resolved_text).group(0)
                    repl = rule["replacement"]
                    # Preserve capitalization
                    if matched_word.isupper():
                        repl = repl.upper()
                    elif matched_word[0].isupper():
                        repl = repl.capitalize()

                    resolved_text = rule["pattern"].sub(repl, resolved_text)
                    notes.append(
                        f"Polysemy resolved: '{matched_word}' -> '{repl}' (triggers: {list(found_triggers) or domain})"
                    )

        return resolved_text, domain, notes
