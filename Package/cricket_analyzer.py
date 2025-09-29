"""
Main cricket analyzer class that orchestrates the PRS calculation process.
"""
import sys
import yaml
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from .match_parser import MatchParser
from .pressure_classifier import PressureClassifier
from .delivery_scorer import DeliveryScorer
from .prs_calculator import PRSCalculator
from .results_formater import ResultsFormatter


class CricketAnalyzer:
    """Main analyzer class that coordinates all components."""
    
    def __init__(self):
        self.parser = MatchParser()
        self.pressure_classifier = PressureClassifier()
        self.scorer = DeliveryScorer()
        self.calculator = PRSCalculator()
        self.formatter = ResultsFormatter()
        self.processed_matches = []
    
    def process_match_file(self, yaml_file: str):
        """Process a single YAML match file."""
        try:
            with open(yaml_file, 'r', encoding='utf-8') as file:
                match_data = yaml.safe_load(file)
        except Exception as e:
            raise Exception(f"Failed to load YAML file: {e}")
        
        # Parse match structure
        match_info = self.parser.parse_match(match_data)
        
        # Process each innings
        for innings_data in match_info['innings']:
            self._process_innings(innings_data, match_info)
        
        self.processed_matches.append({
            'file': yaml_file,
            'info': match_info['info']
        })
    
    def _process_innings(self, innings_data: Dict, match_info: Dict):
        """Process a single innings."""
        deliveries = innings_data['deliveries']
        total_overs = match_info['info'].get('overs', 20)
        total_balls = total_overs * 6
        
        # Track match state
        current_score = 0
        wickets_fallen = 0
        recent_wickets = []
        
        for i, delivery in enumerate(deliveries):
            balls_remaining = total_balls - i - 1
            
            # Update match state
            current_score += delivery['runs']['total']
            if delivery.get('wicket'):
                wickets_fallen += 1
                recent_wickets.append(i)
                # Keep only recent wickets (last 2 overs)
                recent_wickets = [w for w in recent_wickets if i - w <= 12]
            
            # Calculate required run rate if target is known
            target = self._get_target(match_info, innings_data['innings_number'])
            rrr = None
            if target and balls_remaining > 0:
                runs_needed = target - current_score
                overs_remaining = balls_remaining / 6
                rrr = runs_needed / overs_remaining if overs_remaining > 0 else 0
            
            # Classify pressure for this delivery
            pressure_context = self.pressure_classifier.classify_delivery(
                delivery=delivery,
                current_score=current_score,
                wickets_fallen=wickets_fallen,
                balls_remaining=balls_remaining,
                total_overs=total_overs,
                required_run_rate=rrr,
                recent_wickets=len(recent_wickets)
            )
            
            # Score the delivery
            batting_score = self.scorer.score_batting_delivery(delivery, pressure_context)
            bowling_score = self.scorer.score_bowling_delivery(delivery, pressure_context)
            
            # Add to calculator
            self.calculator.add_delivery_performance(
                batsman=delivery['batsman'],
                bowler=delivery['bowler'],
                batting_score=batting_score,
                bowling_score=bowling_score,
                pressure_weight=pressure_context['weight']
            )
    
    def _get_target(self, match_info: Dict, innings_number: int) -> Optional[int]:
        """Get the target score if this is the second innings."""
        if innings_number != 2:
            return None
        
        # In a real implementation, you would track the first innings total
        # For now, we'll return None as we don't have this information easily available
        return None
    
    def display_results(self, format_type: str = 'table', top_n: Optional[int] = None, 
                       include_match_details: bool = False):
        """Display the final PRS results."""
        results = self.calculator.calculate_final_scores()
        
        if format_type == 'json':
            print(json.dumps(results, indent=2))
        elif format_type == 'detailed':
            self.formatter.print_detailed_results(results, top_n, include_match_details)
        else:
            self.formatter.print_table_results(results, top_n)
        
        # Print summary statistics
        if format_type != 'json':
            self._print_summary()
    
    def _print_summary(self):
        """Print analysis summary."""
        total_deliveries = sum(len(p.batting_performances) + len(p.bowling_performances) 
                              for p in self.calculator.players.values())
        print(f"\nAnalysis Summary:", file=sys.stderr if __name__ != '__main__' else None)
        print(f"Matches processed: {len(self.processed_matches)}")
        print(f"Total deliveries analyzed: {total_deliveries}")
        print(f"Players analyzed: {len(self.calculator.players)}")
    
    def process_match_dict(self, data, filename=None):
    
        try:
            # Call your own logic for handling one match dictionary here
            # This is where you plug in logic similar to what you had in your monolithic script.
            print(f"Successfully processed match: {filename}")
            
            # Example stub: you might want to do something like
            # self.extract_player_stats(data)
            
        except Exception as e:
            print(f"Failed to process match {filename}: {e}")

# cricket_analyzer.py

