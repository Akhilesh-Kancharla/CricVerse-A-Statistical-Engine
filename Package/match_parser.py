"""
Parser for cricket match YAML data.
"""

from typing import Dict, List, Any, Optional


class MatchParser:
    """Parses cricket match data from YAML format."""
    
    def parse_match(self, match_data: Dict) -> Dict:
        """Parse the complete match data structure."""
        try:
            info = match_data.get('info', {})
            innings_list = match_data.get('innings', [])
            
            parsed_innings = []
            for i, innings in enumerate(innings_list):
                innings_key = list(innings.keys())[0]  # e.g., '1st innings'
                innings_data = innings[innings_key]
                
                parsed_deliveries = self._parse_deliveries(innings_data.get('deliveries', []))
                
                parsed_innings.append({
                    'innings_number': i + 1,
                    'team': innings_data.get('team'),
                    'deliveries': parsed_deliveries
                })
            
            return {
                'info': info,
                'innings': parsed_innings
            }
        except Exception as e:
            raise Exception(f"Error parsing match data: {e}")
    
    def _parse_deliveries(self, deliveries_data: List[Dict]) -> List[Dict]:
        """Parse individual deliveries from the match data."""
        parsed_deliveries = []
        
        for delivery_dict in deliveries_data:
            # Each delivery is a dict with one key (e.g., '0.1')
            ball_key = list(delivery_dict.keys())[0]
            delivery_data = delivery_dict[ball_key]
            
            # Parse over and ball from key (e.g., '0.1' -> over=0, ball=1)
            try:
                # Ensure ball_key is a string
                over_str, ball_str = str(ball_key).split('.')
                over_num = int(over_str)
                ball_num = int(ball_str)
            except Exception as e:
                raise ValueError(f"Invalid delivery key format '{ball_key}': {e}")

            
            parsed_delivery = {
                'over': over_num,
                'ball': ball_num,
                'batsman': delivery_data.get('batsman'),
                'bowler': delivery_data.get('bowler'),
                'non_striker': delivery_data.get('non_striker'),
                'runs': delivery_data.get('runs', {}),
                'wicket': delivery_data.get('wicket'),
                'extras': delivery_data.get('extras')
            }
            
            parsed_deliveries.append(parsed_delivery)
        
        return parsed_deliveries
    
    def extract_players(self, match_data: Dict) -> Dict[str, List[str]]:
        """Extract player lists by team."""
        try:
            return match_data.get('info', {}).get('players', {})
        except Exception:
            return {}
    
    def get_match_info(self, match_data: Dict) -> Dict:
        """Extract basic match information."""
        info = match_data.get('info', {})
        
        return {
            'match_type': info.get('match_type'),
            'competition': info.get('competition'),
            'venue': info.get('venue'),
            'date': info.get('dates', [None])[0],
            'overs': info.get('overs', 20),
            'balls_per_over': info.get('balls_per_over', 6),
            'teams': info.get('teams', []),
            'toss': info.get('toss', {}),
            'outcome': info.get('outcome', {})
        }