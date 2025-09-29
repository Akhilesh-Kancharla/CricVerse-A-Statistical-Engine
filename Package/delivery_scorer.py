"""
Scores individual deliveries based on performance and pressure context.
"""

from typing import Dict, Any


class DeliveryScorer:
    """Scores batting and bowling performances for individual deliveries."""
    
    def __init__(self):
        # Base scoring weights
        self.batting_weights = {
            'runs_per_ball': 1.0,
            'boundary_bonus': 0.5,
            'dot_ball_penalty': -0.3,
            'dismissal_penalty': -2.0
        }
        
        self.bowling_weights = {
            'dot_ball_bonus': 0.8,
            'wicket_bonus': 3.0,
            'runs_conceded_penalty': -0.2,
            'boundary_penalty': -1.0
        }
    
    def score_batting_delivery(self, delivery: Dict, pressure_context: Dict) -> float:
        """Score a batting performance for a single delivery."""
        runs = delivery.get('runs', {}).get('batsman', 0)
        total_runs = delivery.get('runs', {}).get('total', 0)
        wicket = delivery.get('wicket')
        
        # Base score from runs
        base_score = runs * self.batting_weights['runs_per_ball']
        
        # Boundary bonus
        if runs >= 4:
            base_score += self.batting_weights['boundary_bonus']
        
        # Dot ball penalty (only if no extras)
        if total_runs == 0:
            base_score += self.batting_weights['dot_ball_penalty']
        
        # Dismissal penalty
        if wicket and wicket.get('player_out') == delivery.get('batsman'):
            base_score += self.batting_weights['dismissal_penalty']
        
        # Apply pressure weighting
        pressure_weight = pressure_context['weight']
        weighted_score = base_score * (1.0 + pressure_weight)
        
        return weighted_score
    
    def score_bowling_delivery(self, delivery: Dict, pressure_context: Dict) -> float:
        """Score a bowling performance for a single delivery."""
        runs_conceded = delivery.get('runs', {}).get('total', 0)
        wicket = delivery.get('wicket')
        
        base_score = 0.0
        
        # Dot ball bonus
        if runs_conceded == 0:
            base_score += self.bowling_weights['dot_ball_bonus']
        
        # Wicket bonus
        if wicket:
            base_score += self.bowling_weights['wicket_bonus']
        
        # Runs conceded penalty
        base_score += runs_conceded * self.bowling_weights['runs_conceded_penalty']
        
        # Boundary penalty
        if runs_conceded >= 4:
            base_score += self.bowling_weights['boundary_penalty']
        
        # Apply pressure weighting - bowlers get extra credit for performing under pressure
        pressure_weight = pressure_context['weight']
        weighted_score = base_score * (1.0 + pressure_weight * 0.8)
        
        return weighted_score
    
    def get_scoring_summary(self) -> Dict[str, Any]:
        """Return a summary of the scoring system."""
        return {
            'batting_weights': self.batting_weights,
            'bowling_weights': self.bowling_weights,
            'description': {
                'batting': 'Higher scores for runs, boundaries; penalties for dots, dismissals',
                'bowling': 'Higher scores for dots, wickets; penalties for runs, boundaries',
                'pressure': 'All scores amplified by pressure context (0.2x to 1.0x multiplier)'
            }
        }