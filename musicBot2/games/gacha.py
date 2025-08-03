import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from utils.database import db
from config import config

logger = logging.getLogger(__name__)

@dataclass
class GachaCharacter:
    name: str
    rarity: int
    adjective: str
    drop_rate: float
    sell_value: int
    
    def __str__(self):
        stars = "★" * self.rarity
        return f"{self.rarity}★ {self.adjective} {self.name}"

class GachaSystem:
    def __init__(self):
        self.characters = self._load_characters()
        self.rates = {2: 0.5, 3: 0.35, 4: 0.13, 5: 0.02}
        self.pity_system = {}  # Track pity for each user
    
    def _load_characters(self) -> List[GachaCharacter]:
        """Load character pool with rarity and value information"""
        characters = []
        
        # 2★ characters (50% chance)
        for person in config.person_pool:
            for adjective in config.adjectives_pool[:5]:  # First 5 adjectives for 2★
                characters.append(GachaCharacter(
                    name=person,
                    rarity=2,
                    adjective=adjective,
                    drop_rate=0.5,
                    sell_value=5
                ))
        
        # 3★ characters (35% chance)
        for person in config.person_pool:
            for adjective in config.adjectives_pool[5:10]:  # Next 5 adjectives for 3★
                characters.append(GachaCharacter(
                    name=person,
                    rarity=3,
                    adjective=adjective,
                    drop_rate=0.35,
                    sell_value=15
                ))
        
        # 4★ characters (13% chance)
        for person in config.person_pool:
            for adjective in config.adjectives_pool[10:15]:  # Next 5 adjectives for 4★
                characters.append(GachaCharacter(
                    name=person,
                    rarity=4,
                    adjective=adjective,
                    drop_rate=0.13,
                    sell_value=50
                ))
        
        # 5★ characters (2% chance)
        for person in config.person_pool:
            for adjective in config.adjectives_pool[15:]:  # Last 5 adjectives for 5★
                characters.append(GachaCharacter(
                    name=person,
                    rarity=5,
                    adjective=adjective,
                    drop_rate=0.02,
                    sell_value=200
                ))
        
        return characters
    
    def _get_pity_info(self, user_id: str) -> Dict[str, int]:
        """Get pity information for user"""
        if user_id not in self.pity_system:
            self.pity_system[user_id] = {'pulls': 0, 'last_4_star': 0, 'last_5_star': 0}
        return self.pity_system[user_id]
    
    def _update_pity(self, user_id: str, rarity: int):
        """Update pity counters"""
        pity = self._get_pity_info(user_id)
        pity['pulls'] += 1
        
        if rarity >= 4:
            pity['last_4_star'] = pity['pulls']
        if rarity >= 5:
            pity['last_5_star'] = pity['pulls']
    
    def _apply_pity(self, user_id: str) -> Optional[int]:
        """Apply pity system - guaranteed 4★ after 50 pulls, 5★ after 100 pulls"""
        pity = self._get_pity_info(user_id)
        
        # Guaranteed 5★ after 100 pulls without one
        if pity['pulls'] - pity['last_5_star'] >= 100:
            return 5
        
        # Guaranteed 4★ after 50 pulls without one
        if pity['pulls'] - pity['last_4_star'] >= 50:
            return 4
        
        return None
    
    async def pull(self, user_id: str) -> Dict[str, Any]:
        """Perform a gacha pull"""
        # Check pity first
        guaranteed_rarity = self._apply_pity(user_id)
        
        if guaranteed_rarity:
            # Guaranteed pull
            available_chars = [char for char in self.characters if char.rarity == guaranteed_rarity]
            selected_char = random.choice(available_chars)
        else:
            # Normal pull with rates
            rand = random.random()
            cumulative_rate = 0
            
            for rarity, rate in self.rates.items():
                cumulative_rate += rate
                if rand <= cumulative_rate:
                    available_chars = [char for char in self.characters if char.rarity == rarity]
                    selected_char = random.choice(available_chars)
                    break
            else:
                # Fallback to 2★
                available_chars = [char for char in self.characters if char.rarity == 2]
                selected_char = random.choice(available_chars)
        
        # Update pity
        self._update_pity(user_id, selected_char.rarity)
        
        # Add to database
        await db.add_gacha_item(user_id, selected_char.name, selected_char.rarity, selected_char.adjective)
        
        return {
            'character': selected_char,
            'rarity': selected_char.rarity,
            'pity_pulls': self._get_pity_info(user_id)['pulls'],
            'next_guaranteed_4': max(0, 50 - (self._get_pity_info(user_id)['pulls'] - self._get_pity_info(user_id)['last_4_star'])),
            'next_guaranteed_5': max(0, 100 - (self._get_pity_info(user_id)['pulls'] - self._get_pity_info(user_id)['last_5_star']))
        }
    
    async def get_inventory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive inventory statistics"""
        inventory = await db.get_gacha_inventory(user_id)
        
        if not inventory:
            return {
                'total_characters': 0,
                'rarity_counts': {2: 0, 3: 0, 4: 0, 5: 0},
                'total_value': 0,
                'rarest_character': None
            }
        
        rarity_counts = {2: 0, 3: 0, 4: 0, 5: 0}
        total_value = 0
        rarest_character = None
        
        for item in inventory:
            rarity_counts[item['rarity']] += 1
            # Calculate sell value based on rarity
            sell_value = {2: 5, 3: 15, 4: 50, 5: 200}[item['rarity']]
            total_value += sell_value
            
            if rarest_character is None or item['rarity'] > rarest_character['rarity']:
                rarest_character = item
        
        return {
            'total_characters': len(inventory),
            'rarity_counts': rarity_counts,
            'total_value': total_value,
            'rarest_character': rarest_character
        }
    
    def get_rarity_color(self, rarity: int) -> int:
        """Get Discord color for rarity"""
        colors = {
            2: 0x808080,  # Gray
            3: 0x00FF00,  # Green
            4: 0x0000FF,  # Blue
            5: 0xFFD700   # Gold
        }
        return colors.get(rarity, 0x808080)
    
    def get_rarity_emoji(self, rarity: int) -> str:
        """Get emoji for rarity"""
        emojis = {
            2: "⚪",
            3: "🟢",
            4: "🔵",
            5: "🟡"
        }
        return emojis.get(rarity, "⚪")

# Global gacha system instance
gacha_system = GachaSystem() 