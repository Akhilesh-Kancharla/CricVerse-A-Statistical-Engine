"""
Classifies the pressure level of each delivery based on match context.
"""

from typing import Dict, Optional
from enum import Enum


class PressureLevel(Enum):
    """Enumeration of pressure levels."""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    EXTREME = 5


class PressureClassifier:
    """Classifies deliveries into pressure zones based on match context."""
    
    def __init__(self):
        # Pressure weights for different levels
        self.pressure_weights = {
            PressureLevel.VERY_LOW: 0.2,
            PressureLevel.LOW: 0.4,
            PressureLevel.MEDIUM: 0.6,
            PressureLevel.HIGH: 0.8,
            PressureLevel.EXTREME: 1.0
        }
    
    def classify_delivery(self, delivery: Dict, current_score: int, wickets_fallen: int,
                         balls_remaining: int, total_overs: int, required_run_rate: Optional[float],
                         recent_wickets: int) -> Dict:
        """Classify a single delivery's pressure level."""
        
        pressure_factors = self._calculate_pressure_factors(
            delivery, current_score, wickets_fallen, balls_remaining,
            total_overs, required_run_rate, recent_wickets
        )
        
        pressure_level = self._determine_pressure_level(pressure_factors)
        
        return {
            'level': pressure_level,
            'weight': self.pressure_weights[pressure_level],
            'factors': pressure_factors
        }
    
    def _calculate_pressure_factors(self, delivery: Dict, current_score: int,
                                   wickets_fallen: int, balls_remaining: int,
                                   total_overs: int, required_run_rate: Optional[float],
                                   recent_wickets: int) -> Dict:
        """Calculate various pressure factors for the delivery."""
        
        over_num = delivery['over']
        total_balls = total_overs * 6
        balls_bowled = total_balls - balls_remaining
        
        factors = {
            'phase_pressure': self._calculate_phase_pressure(over_num, total_overs),
            'wicket_pressure': self._calculate_wicket_pressure(wickets_fallen, recent_wickets),
            'run_rate_pressure': self._calculate_run_rate_pressure(required_run_rate),
            'balls_remaining_pressure': self._calculate_balls_remaining_pressure(balls_remaining, total_balls),
            'situation_pressure': self._calculate_situation_pressure(delivery)
        }
        
        return factors
    
    def _calculate_phase_pressure(self, over_num: int, total_overs: int) -> float:
        """Calculate pressure based on the phase of the match."""
        if total_overs <= 6:  # T20 powerplay
            if over_num < 6:
                return 0.3  # Powerplay - moderate pressure
            elif over_num >= total_overs - 4:
                return 0.9  # Death overs - high pressure
            else:
                return 0.5  # Middle overs - medium pressure
        else:  # Longer format
            overs_proportion = over_num / total_overs
            if overs_proportion < 0.3:
                return 0.2  # Early overs
            elif overs_proportion > 0.8:
                return 0.8  # Final overs
            else:
                return 0.4  # Middle overs
    
    def _calculate_wicket_pressure(self, wickets_fallen: int, recent_wickets: int) -> float:
        """Calculate pressure based on wickets situation."""
        base_pressure = min(wickets_fallen / 10.0, 0.8)  # More wickets = more pressure
        recent_wicket_bonus = min(recent_wickets * 0.2, 0.4)
        return min(base_pressure + recent_wicket_bonus, 1.0)
    
    def _calculate_run_rate_pressure(self, required_run_rate: Optional[float]) -> float:
        """Calculate pressure based on required run rate."""
        if required_run_rate is None:
            return 0.3  # Default moderate pressure for first innings
        
        if required_run_rate <= 6:
            return 0.2
        elif required_run_rate <= 8:
            return 0.4
        elif required_run_rate <= 10:
            return 0.6
        elif required_run_rate <= 12:
            return 0.8
        else:
            return 1.0
    
    def _calculate_balls_remaining_pressure(self, balls_remaining: int, total_balls: int) -> float:
        """Calculate pressure based on balls remaining."""
        proportion_remaining = balls_remaining / total_balls
        
        if proportion_remaining > 0.8:
            return 0.1  # Plenty of time
        elif proportion_remaining > 0.5:
            return 0.3  # Moderate time pressure
        elif proportion_remaining > 0.2:
            return 0.6  # Increasing pressure
        elif proportion_remaining > 0.1:
            return 0.8  # High pressure
        else:
            return 1.0  # Extreme pressure
    
    def _calculate_situation_pressure(self, delivery: Dict) -> float:
        """Calculate pressure based on specific delivery situation."""
        pressure = 0.0
        
        # Wicket delivery increases pressure
        if delivery.get('wicket'):
            pressure += 0.3
        
        # Boundary conceded/scored affects pressure
        runs = delivery.get('runs', {}).get('total', 0)
        if runs >= 4:
            pressure += 0.2
        elif runs == 0:
            pressure += 0.1  # Dot ball pressure
        
        return min(pressure, 0.5)
    
    def _determine_pressure_level(self, factors: Dict) -> PressureLevel:
        """Determine overall pressure level from individual factors."""
        # Weighted average of all pressure factors
        weights = {
            'phase_pressure': 0.25,
            'wicket_pressure': 0.25,
            'run_rate_pressure': 0.25,
            'balls_remaining_pressure': 0.15,
            'situation_pressure': 0.1
        }
        
        total_pressure = sum(factors[factor] * weight for factor, weight in weights.items())
        
        if total_pressure <= 0.3:
            return PressureLevel.VERY_LOW
        elif total_pressure <= 0.45:
            return PressureLevel.LOW
        elif total_pressure <= 0.6:
            return PressureLevel.MEDIUM
        elif total_pressure <= 0.8:
            return PressureLevel.HIGH
        else:
            return PressureLevel.EXTREME