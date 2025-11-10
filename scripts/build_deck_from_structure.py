#!/usr/bin/env python3
"""Convert structured v3 deck JSON into a 100-card list using the Prisma SQLite DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "prisma" / "dev.db"
OUTPUT_DIR = REPO_ROOT / "generated_decks" / "v3_executed"


@dataclass
class Card:
    name: str
    type_line: str
    oracle_text: str
    cmc: float
    colors: List[str]
    color_identity: List[str]
    keywords: List[str]
    edhrec_rank: Optional[int]
    is_commander: bool


def load_cards() -> List[Card]:
    if not DB_PATH.exists():
        raise SystemExit(f"SQLite DB not found at {DB_PATH}. Run `npx prisma db push`/imports first.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT name, typeLine, oracleText, cmc, colors, colorIdentity,
               keywords, edhrecRank, isCommander
        FROM Card
        """
    ).fetchall()
    conn.close()

    def parse_csv(value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [token.strip().upper() for token in value.split(',') if token.strip()]

    cards: List[Card] = []
    for row in rows:
        cards.append(
            Card(
                name=row["name"],
                type_line=row["typeLine"] or "",
                oracle_text=row["oracleText"] or "",
                cmc=row["cmc"] or 0.0,
                colors=parse_csv(row["colors"]),
                color_identity=parse_csv(row["colorIdentity"]),
                keywords=parse_csv(row["keywords"]),
                edhrec_rank=row["edhrecRank"] if row["edhrecRank"] is not None else None,
                is_commander=bool(row["isCommander"]),
            )
        )
    return cards


def infer_tags(card: Card) -> Set[str]:
    tags: Set[str] = set()
    text = card.oracle_text.lower()
    type_line = card.type_line.lower()

    def add(tag: str) -> None:
        if tag:
            tags.add(tag)

    if "add {" in text or "treasure token" in text or "search your library for a land" in text:
        add("ramp")
    if "draw" in text or "investigate" in text:
        add("card_draw")
    if "destroy target" in text or "exile target" in text or ("deal" in text and "damage" in text and "target" in text):
        add("removal")
    if "destroy all" in text or "each creature" in text:
        add("board_wipe")
    if "search your library" in text:
        add("tutor")
    if "hexproof" in text or "indestructible" in text or "protection from" in text:
        add("protection")
    if "counter target" in text:
        add("counterspell")
    if "token" in text:
        add("tokens")
    if "graveyard" in text:
        add("graveyard")
    if "sacrifice" in text:
        add("sacrifice")
    if "+1/+1 counter" in text or "proliferate" in text:
        add("counters")
    if "haste" in text:
        add("haste")

    tribe_map = {
        "dragon": "tribal_dragons",
        "goblin": "tribal_goblins",
        "elf": "tribal_elves",
        "zombie": "tribal_zombies",
        "angel": "tribal_angels",
        "sliver": "tribal_slivers",
        "soldier": "tribal_soldiers",
    }
    for subtype, tag in tribe_map.items():
        if subtype in type_line:
            add(tag)

    if card.edhrec_rank and card.edhrec_rank < 200:
        add("staple")
    if card.is_commander:
        add("commander")
    return tags


def colors_subset(card_colors: Sequence[str], allowed: Sequence[str]) -> bool:
    if not allowed:
        return True
    return all(color in allowed for color in card_colors)


def pick_cards(
    cards: List[Card],
    needed: int,
    used: Set[str],
    commander: Optional[Card],
    filter_spec: Dict[str, Any],
) -> List[Card]:
    candidates = [card for card in cards if card.name.lower() not in used]

    types = [t.lower() for t in filter_spec.get("types", [])]
    if types:
        candidates = [card for card in candidates if all(t in card.type_line.lower() for t in types)]

    subtypes = [t.lower() for t in filter_spec.get("subtypes", [])]
    if subtypes:
        candidates = [card for card in candidates if all(t in card.type_line.lower() for t in subtypes)]

    colors_within = [c.upper() for c in filter_spec.get("colors_within", [])]
    if colors_within:
        candidates = [card for card in candidates if colors_subset(card.color_identity, colors_within)]
    elif commander:
        candidates = [card for card in candidates if colors_subset(card.color_identity, commander.color_identity)]

    cmc_max = filter_spec.get("cmc_max")
    if cmc_max is not None:
        candidates = [card for card in candidates if card.cmc <= cmc_max]

    cmc_min = filter_spec.get("cmc_min")
    if cmc_min is not None:
        candidates = [card for card in candidates if card.cmc >= cmc_min]

    if filter_spec.get("instant_speed"):
        candidates = [card for card in candidates if "instant" in card.type_line.lower()]

    tag_filters = filter_spec.get("tags") or []
    if tag_filters:
        candidates = [card for card in candidates if infer_tags(card).issuperset(tag_filters)]

    candidates.sort(key=lambda c: c.edhrec_rank or 999999)
    return candidates[:needed]


def pick_staples(cards: List[Card], needed: int, used: Set[str], commander: Optional[Card]) -> List[Card]:
    commander_colors = commander.color_identity if commander else []
    staples = [
        card
        for card in cards
        if card.name.lower() not in used
        and colors_subset(card.color_identity, commander_colors)
        and (card.edhrec_rank or 999999) < 8000
    ]
    staples.sort(key=lambda c: c.edhrec_rank or 999999)
    return staples[:needed]


def fill_basics(needed: int, commander: Optional[Card]) -> List[str]:
    color_order = commander.color_identity if commander else []
    basics_map = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
    if not color_order:
        return ["Wastes"] * needed
    result: List[str] = []
    for i in range(needed):
        color = color_order[i % len(color_order)]
        result.append(basics_map.get(color, "Wastes"))
    return result


def build_deck(plan: Dict[str, Any], cards: List[Card]) -> Dict[str, Any]:
    used: Set[str] = set()
    result_cards: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []

    commander_name = plan.get("commander") or (plan.get("commanders") or [None])[0]
    commander_card = next((card for card in cards if card.name.lower() == (commander_name or '').lower()), None)
    if commander_card:
        result_cards.append({"name": commander_card.name, "role": "commander"})
        used.add(commander_card.name.lower())
    else:
        warnings.append("No commander found in card database; deck will be colorless.")

    card_selection: Dict[str, Any] = plan.get("card_selection") or {}
    for category, section in card_selection.items():
        if not section:
            continue
        target = int(section.get("count", 0))
        if target <= 0:
            continue
        filters = section.get("filters") or [{}]
        per_filter = max(1, target // len(filters))
        collected = 0
        for filter_spec in filters:
            if collected >= target:
                break
            need = min(per_filter, target - collected)
            picked = pick_cards(cards, need, used, commander_card, filter_spec)
            if not picked:
                warnings.append(f"Category {category}: no matches for filter {filter_spec}; using staples.")
                picked = pick_staples(cards, need, used, commander_card)
            for card in picked:
                result_cards.append({"name": card.name, "role": category, "reason": filter_spec.get("reason")})
                used.add(card.name.lower())
                collected += 1
        while collected < target:
            filler = pick_staples(cards, 1, used, commander_card)
            if not filler:
                break
            card = filler[0]
            result_cards.append({"name": card.name, "role": category})
            used.add(card.name.lower())
            collected += 1

    if len(result_cards) < 100:
        basics = fill_basics(100 - len(result_cards), commander_card)
        for name in basics:
            result_cards.append({"name": name, "role": "land", "reason": "Auto-fill basic land"})
        warnings.append(f"Deck padded with {len(basics)} basic lands to reach 100 cards.")
    elif len(result_cards) > 100:
        warnings.append(f"Deck exceeded 100 cards by {len(result_cards) - 100}; trimming extras from the end.")
        result_cards = result_cards[:100]

    return {
        "commander": commander_card.name if commander_card else None,
        "cards": result_cards,
        "warnings": warnings,
        "errors": errors,
    }


def execute_plan(plan: Dict[str, Any], cards: Optional[List[Card]] = None) -> Dict[str, Any]:
    card_pool = cards or load_cards()
    return build_deck(plan, card_pool)


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute structured deck JSON into a 100-card list.")
    parser.add_argument("plan", help="Path to structured JSON file.")
    parser.add_argument("--out", help="Output directory", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        raise SystemExit(f"Structured JSON not found: {plan_path}")

    plan = json.loads(plan_path.read_text())
    deck = execute_plan(plan)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (plan_path.stem + "-deck.json")
    out_path.write_text(json.dumps(deck, indent=2))

    print(f"Commander: {deck['commander']}")
    print(f"Cards: {len(deck['cards'])}")
    if deck["warnings"]:
        print("Warnings:")
        for warn in deck["warnings"]:
            print(f"  - {warn}")
    if deck["errors"]:
        print("Errors:")
        for err in deck["errors"]:
            print(f"  - {err}")
    print(f"Deck saved to {out_path}")


if __name__ == "__main__":
    main()
