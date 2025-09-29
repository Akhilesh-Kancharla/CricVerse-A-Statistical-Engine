"""
Calculates the final Pressure Resistance Score (PRS) for each player.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class PlayerPerformance:
    """Stores performance data for a single player."""
    batting_performances: List[float] = field(default_factory=list)
    bowling_performances: List[float] = field(default_factory=list)
    batting_pressure_weights: List[float] = field(default_factory=list)
    bowling_pressure_weights: List[float] = field(default_factory=list)


class PRSCalculator:
    """Calculates Pressure Resistance Scores for all players."""
    
    def __init__(self):
        self.players: Dict[str, PlayerPerformance] = defaultdict(PlayerPerformance)
        
    def add_delivery_performance(self, batsman: str, bowler: str, 
                               batting_score: float, bowling_score: float,
                               pressure_weight: float):
        """Add performance data for a single delivery."""
        # Add batting performance
        self.players[batsman].batting_performances.append(batting_score)
        self.players[batsman].batting_pressure_weights.append(pressure_weight)
        
        # Add bowling performance
        self.players[bowler].bowling_performances.append(bowling_score)
        self.players[bowler].bowling_pressure_weights.append(pressure_weight)
    
    def calculate_final_scores(self) -> Dict[str, Dict[str, Any]]:
        """Calculate final PRS scores for all players."""
        results = {}
        
        for player_name, performance in self.players.items():
            batting_prs = self._calculate_prs(
                performance.batting_performances,
                performance.batting_pressure_weights
            )
            
            bowling_prs = self._calculate_prs(
                performance.bowling_performances,
                performance.bowling_pressure_weights
            )
            
            results[player_name] = {
                'batting_prs': batting_prs,
                'bowling_prs': bowling_prs,
                'batting_deliveries': len(performance.batting_performances),
                'bowling_deliveries': len(performance.bowling_performances),
                'total_deliveries': len(performance.batting_performances) + len(performance.bowling_performances)
            }
        
        return results
    
    def _calculate_prs(self, performances: List[float], pressure_weights: List[float]) -> float:
        """Calculate PRS for a specific discipline (batting or bowling)."""
        if not performances:
            return 0.0
        
        # Calculate weighted average performance
        total_weighted_score = sum(score * weight for score, weight in zip(performances, pressure_weights))
        total_weight = sum(pressure_weights)
        
        if total_weight == 0:
            return 0.0
        
        weighted_average = total_weighted_score / total_weight
        
        # Normalize to a 0-100 scale
        # This is a simplified normalization - in practice, you might want to use
        # historical data to establish proper scaling
        base_prs = max(0, min(100, 50 + weighted_average * 10))
        
        return round(base_prs, 1)
    
    def get_player_summary(self, player_name: str) -> Dict[str, Any]:
        """Get detailed summary for a specific player."""
        if player_name not in self.players:
            return {}
        
        performance = self.players[player_name]
        
        batting_stats = self._get_discipline_stats(
            performance.batting_performances,
            performance.batting_pressure_weights
        )
        
        bowling_stats = self._get_discipline_stats(
            performance.bowling_performances,
            performance.bowling_pressure_weights
        )
        
        return {
            'batting': batting_stats,
            'bowling': bowling_stats
        }
    
    def _get_discipline_stats(self, performances: List[float], weights: List[float]) -> Dict[str, Any]:
        """Get detailed statistics for a discipline (batting/bowling)."""
        if not performances:
            return {
                'deliveries': 0,
                'average_score': 0.0,
                'weighted_average': 0.0,
                'best_performance': 0.0,
                'worst_performance': 0.0,
                'pressure_adjusted_score': 0.0
            }
        
        average_score = sum(performances) / len(performances)
        weighted_average = sum(p * w for p, w in zip(performances, weights)) / sum(weights) if weights else 0
        
        return {
            'deliveries': len(performances),
            'average_score': round(average_score, 2),
            'weighted_average': round(weighted_average, 2),
            'best_performance': round(max(performances), 2),
            'worst_performance': round(min(performances), 2),
            'average_pressure': round(sum(weights) / len(weights), 2) if weights else 0
        }