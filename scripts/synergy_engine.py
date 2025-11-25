import subprocess
import json

class SynergyEngine:
    def __init__(self, color_checker=None, db_path=None):
        self.color_checker = color_checker
        self.db_path = db_path
        
        # Format: 'Card Name': ['Synergistic Card 1', 'Synergistic Card 2']
        self.HARDCODED_SYNERGIES = {
            # ... (keep existing hardcoded synergies) ...
            # Sanguine Bond / Exquisite Blood Combo
            'Exquisite Blood': ['Sanguine Bond', 'Vito, Thorn of the Dusk Rose', 'Cliffhaven Vampire'],
            'Sanguine Bond': ['Exquisite Blood', 'Vito, Thorn of the Dusk Rose'],
            'Vito, Thorn of the Dusk Rose': ['Exquisite Blood'],
            
            # Urza Tron
            "Urza's Tower": ["Urza's Mine", "Urza's Power Plant"],
            "Urza's Mine": ["Urza's Tower", "Urza's Power Plant"],
            "Urza's Power Plant": ["Urza's Tower", "Urza's Mine"],
            
            # Kiki-Jiki Lines
            'Kiki-Jiki, Mirror Breaker': ['Zealous Conscripts', 'Restoration Angel', 'Village Bell-Ringer'],
            'Zealous Conscripts': ['Kiki-Jiki, Mirror Breaker', 'Splinter Twin'],
            
            # Heliod Ballista
            'Heliod, Sun-Crowned': ['Walking Ballista'],
            'Walking Ballista': ['Heliod, Sun-Crowned'],
            
            # Thassa's Oracle
            "Thassa's Oracle": ['Demonic Consultation', 'Tainted Pact'],
            'Demonic Consultation': ["Thassa's Oracle", 'Laboratory Maniac', 'Jace, Wielder of Mysteries'],
            
            # Isochron Scepter
            'Isochron Scepter': ['Dramatic Reversal'],
            'Dramatic Reversal': ['Isochron Scepter'],
            
            # Godo
            'Godo, Bandit Warlord': ['Helm of the Host'],
            'Helm of the Host': ['Godo, Bandit Warlord', 'Aurelia, the Warleader'],
            
            # Dualcaster
            'Dualcaster Mage': ['Twinflame', 'Heat Shimmer'],
            'Twinflame': ['Dualcaster Mage'],
        }

    def find_synergies(self, current_deck, commander_colors):
        """
        Returns a list of cards to add based on synergies with existing cards.
        """
        suggestions = []
        current_set = set(current_deck)
        
        # 1. Check Hardcoded Synergies
        for card in current_deck:
            if card in self.HARDCODED_SYNERGIES:
                potential_adds = self.HARDCODED_SYNERGIES[card]
                for candidate in potential_adds:
                    if candidate not in current_set and candidate not in suggestions:
                        suggestions.append(candidate)
        
        # 2. Check Database Synergies (via CLI subprocess)
        if self.db_path:
            try:
                # We'll query for all cards in the deck at once to minimize subprocess calls?
                # Or just loop. Looping is safer for escaping.
                # Actually, we can use a single query with OR? No, too complex.
                # Let's just loop for now. 100 calls is fine locally.
                
                for card in current_deck:
                    # Escape single quotes for CLI
                    escaped_card = card.replace("'", "''")
                    
                    query = f"""
                        SELECT S_Card.name, Syn.score 
                        FROM CardSynergy Syn
                        JOIN Card C_Source ON Syn.cardId = C_Source.id
                        JOIN Card S_Card ON Syn.synergyId = S_Card.id
                        WHERE C_Source.name = '{escaped_card}' 
                        AND Syn.score > 15
                        ORDER BY Syn.score DESC
                        LIMIT 2;
                    """
                    
                    # Run sqlite3 CLI
                    result = subprocess.run(
                        ['sqlite3', self.db_path, query],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if '|' in line:
                                candidate = line.split('|')[0].strip()
                                if candidate not in current_set and candidate not in suggestions:
                                    # print(f"   🧩 DB Synergy (CLI): {card} -> {candidate}")
                                    suggestions.append(candidate)
                            
                            
            except Exception as e:
                print(f"   ⚠️ Error querying synergy DB via CLI: {e}")

        # 3. Check Database Combos (via CLI subprocess)
        if self.db_path:
            try:
                # Find combos involving current cards
                # We need to find combos where we have at least one piece, and suggest the missing pieces.
                # Logic:
                # 1. Find all ComboIDs linked to cards in our deck.
                # 2. For each ComboID, get all CardIDs in that combo.
                # 3. If we have some but not all, suggest the missing ones.
                
                # This is a bit complex for a simple loop. Let's try to get relevant combos in one go.
                # We can iterate over cards in deck, and for each, find combos it belongs to.
                
                for card in current_deck:
                    escaped_card = card.replace("'", "''")
                    
                    # Get combos this card is part of
                    # We want the Combo ID, Name, and ALL cards in it.
                    # But SQLite return format is flat.
                    # Let's just get the Combo IDs first.
                    
                    query_combos = f"""
                        SELECT DISTINCT C.id, C.name, C.result
                        FROM Combo C
                        JOIN ComboCard CC ON C.id = CC.comboId
                        JOIN Card Card ON CC.cardId = Card.id
                        WHERE Card.name = '{escaped_card}';
                    """
                    
                    result = subprocess.run(
                        ['sqlite3', self.db_path, query_combos],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        combo_lines = result.stdout.strip().split('\n')
                        for line in combo_lines:
                            if '|' not in line: continue
                            parts = line.split('|')
                            combo_id = parts[0]
                            combo_name = parts[1]
                            combo_result = parts[2] if len(parts) > 2 else "Combo"
                            
                            # Now get all cards for this combo
                            query_cards = f"""
                                SELECT Card.name
                                FROM ComboCard CC
                                JOIN Card Card ON CC.cardId = Card.id
                                WHERE CC.comboId = '{combo_id}';
                            """
                            
                            res_cards = subprocess.run(
                                ['sqlite3', self.db_path, query_cards],
                                capture_output=True,
                                text=True
                            )
                            
                            if res_cards.returncode == 0 and res_cards.stdout.strip():
                                combo_cards = [c.strip() for c in res_cards.stdout.strip().split('\n')]
                                
                                # Check what we have vs what we need
                                missing = [c for c in combo_cards if c not in current_set]
                                
                                # If we have at least 1 piece (which we do, 'card') and are missing at least 1
                                # And we aren't missing TOO many (e.g. don't suggest a 5 card combo if we only have 1)
                                # Let's say: suggest if we have >= 50% of the combo OR if it's a 2-card combo and we have 1.
                                
                                has_count = len(combo_cards) - len(missing)
                                total_count = len(combo_cards)
                                
                                should_suggest = False
                                if total_count == 2 and has_count == 1:
                                    should_suggest = True
                                elif total_count > 2 and has_count >= (total_count / 2):
                                    should_suggest = True
                                    
                                if should_suggest:
                                    for m in missing:
                                        if m not in suggestions:
                                            # print(f"   🔥 Combo Found: {combo_name} ({combo_result}) -> Suggesting {m}")
                                            suggestions.append(m)

            except Exception as e:
                print(f"   ⚠️ Error querying combo DB via CLI: {e}")
                    
        return suggestions
