import random
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from utils.database import db
from utils.error_handler import handle_errors
from config import config

logger = logging.getLogger(__name__)

class GamblingManager:
    def __init__(self):
        self.cooldowns: Dict[str, datetime] = {}
        self.daily_limits = {}
    
    async def check_gambling_limits(self, user_id: str, bet_amount: int) -> Tuple[bool, str]:
        """Check if user can gamble with given amount"""
        # Check cooldown
        if user_id in self.cooldowns:
            time_diff = datetime.now() - self.cooldowns[user_id]
            if time_diff.total_seconds() < config.gambling_cooldown:
                remaining = config.gambling_cooldown - time_diff.total_seconds()
                return False, f"⏰ Please wait {remaining:.1f} seconds before gambling again."
        
        # Check daily limit
        daily_total = await db.get_daily_bet_total(user_id)
        if daily_total + bet_amount > config.max_daily_bet:
            return False, f"❌ Daily betting limit exceeded. You've bet ${daily_total} today."
        
        # Check user balance
        balance = await db.get_balance(user_id)
        if bet_amount > balance:
            return False, "❌ You don't have enough money for this bet."
        
        return True, ""
    
    async def apply_gambling_cooldown(self, user_id: str):
        """Apply cooldown after gambling"""
        self.cooldowns[user_id] = datetime.now()
    
    async def record_gambling_activity(self, user_id: str, game_type: str, bet_amount: int, win_amount: int):
        """Record gambling activity"""
        await db.record_gambling(user_id, game_type, bet_amount, win_amount)
        await db.update_daily_bet_total(user_id, bet_amount)
        await self.apply_gambling_cooldown(user_id)

class HigherLowerGame:
    def __init__(self):
        self.active_games: Dict[str, Dict] = {}
    
    async def start_game(self, user_id: str, bet_amount: int) -> Dict[str, Any]:
        """Start a higher/lower game"""
        current_number = random.randint(1, 10)
        self.active_games[user_id] = {
            'current_number': current_number,
            'bet_amount': bet_amount,
            'started_at': datetime.now()
        }
        
        return {
            'current_number': current_number,
            'message': f'The current number is **{current_number}**. Will the next be higher or lower?'
        }
    
    async def process_guess(self, user_id: str, guess: str) -> Dict[str, Any]:
        """Process user's higher/lower guess"""
        if user_id not in self.active_games:
            return {'error': 'No active game found.'}
        
        game_data = self.active_games[user_id]
        current_number = game_data['current_number']
        bet_amount = game_data['bet_amount']
        
        # Generate next number (different from current)
        possible_numbers = [num for num in range(1, 11) if num != current_number]
        next_number = random.choice(possible_numbers)
        
        # Determine if user won
        player_guess = guess.lower()
        win = (player_guess == 'higher' and next_number > current_number) or \
              (player_guess == 'lower' and next_number < current_number)
        
        # Calculate winnings
        if win:
            win_amount = bet_amount
            new_balance = await db.update_balance(user_id, bet_amount)
            result_message = f"🎉 **You won!** The next number was **{next_number}**."
        else:
            win_amount = 0
            new_balance = await db.update_balance(user_id, -bet_amount)
            result_message = f"💔 **You lost!** The next number was **{next_number}**."
        
        # Record gambling activity
        await gambling_manager.record_gambling_activity(user_id, "higher_lower", bet_amount, win_amount)
        
        # Clean up game
        del self.active_games[user_id]
        
        return {
            'win': win,
            'next_number': next_number,
            'win_amount': win_amount,
            'new_balance': new_balance,
            'message': result_message
        }

class SlotMachine:
    def __init__(self):
        self.symbols = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
        self.payouts = {
            "🍒": 5,
            "🍋": 10,
            "🔔": 20,
            "💎": 100,
            "7️⃣": 15
        }
    
    async def spin(self, user_id: str, bet_amount: int) -> Dict[str, Any]:
        """Spin the slot machine"""
        # Generate 3x3 grid
        grid = []
        for _ in range(3):
            row = random.choices(self.symbols, k=3)
            grid.append(row)
        
        # Calculate winnings
        win_amount = 0
        
        # Check horizontal lines
        for row in grid:
            if len(set(row)) == 1:  # All symbols in row are the same
                symbol = row[0]
                win_amount += self.payouts[symbol]
        
        # Check diagonal lines
        if grid[0][0] == grid[1][1] == grid[2][2]:  # Top-left to bottom-right
            symbol = grid[1][1]
            win_amount += self.payouts[symbol] // 2  # Half payout for diagonal
        
        if grid[0][2] == grid[1][1] == grid[2][0]:  # Top-right to bottom-left
            symbol = grid[1][1]
            win_amount += self.payouts[symbol] // 2
        
        # Check for jackpot (all diamonds)
        if all(symbol == "💎" for row in grid for symbol in row):
            win_amount = 10000000
        
        # Update balance
        if win_amount > 0:
            new_balance = await db.update_balance(user_id, win_amount)
            result_message = f"🎉 **You won ${win_amount}!**"
        else:
            new_balance = await db.update_balance(user_id, -bet_amount)
            result_message = "Sorry, you didn't win anything. Better luck next time!"
        
        # Record gambling activity
        await gambling_manager.record_gambling_activity(user_id, "slots", bet_amount, win_amount)
        
        return {
            'grid': grid,
            'win_amount': win_amount,
            'new_balance': new_balance,
            'message': result_message
        }

class AlexRoulette:
    def __init__(self):
        self.special_outcomes = {
            90: {"message": "ggs", "url": "https://www.youtube.com/watch?v=1EUoIhob8t8"},
            10: {"message": "ff", "url": "https://www.youtube.com/watch?v=d3h1I3QDEHU"},
            20: {"message": "My favorite song", "url": "https://www.youtube.com/watch?v=VZZCXP_rFKk"}
        }
    
    async def spin(self, user_id: str) -> Dict[str, Any]:
        """Spin Alex's roulette"""
        roulette_num = random.randint(1, 100)
        
        if roulette_num in self.special_outcomes:
            outcome = self.special_outcomes[roulette_num]
            return {
                'number': roulette_num,
                'special': True,
                'message': outcome['message'],
                'url': outcome['url']
            }
        else:
            return {
                'number': roulette_num,
                'special': False,
                'message': "Thanks for the $10 xD, try again?"
            }

# Global instances
gambling_manager = GamblingManager()
higher_lower_game = HigherLowerGame()
slot_machine = SlotMachine()
alex_roulette = AlexRoulette() 