"""
Formats and displays the final PRS results in various formats.
"""

import sys
import json
import sqlite3
from typing import Dict, Any, Optional, List


class ResultsFormatter:
    """Formats PRS results for display."""
    @staticmethod
    def add_data(data):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        
        try:
            cursor.execute('''
                INSERT INTO prm (
                    player_name,batting_prs,bowling_prs,bat_balls,bowl_balls
                ) VALUES (?, ?, ?, ?, ? )
            ''', (
                data[0], data[1], data[2], data[3], data[4]
            ))
            conn.commit()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print("Table not found, creating one...")
                cursor.execute('''
                    CREATE TABLE prm (
                        player_name TEXT,
                        batting_prs INTEGER,
                        bowling_prs INTEGER,
                        bat_balls INTEGER,
                        bowl_balls INTEGER,
                        PRIMARY KEY (player_name)
                    )
                ''')
                conn.commit()

                # retry the insert
                cursor.execute('''
                    INSERT INTO prm (
                        player_name,batting_prs,bowling_prs,bat_balls,bowl_balls
                    ) VALUES (?, ?, ?, ?, ? )
                ''', (
                    data[0], data[1], data[2], data[3], data[4]
                ))
                conn.commit()
            else:
                print("Error inserting:", e)
                conn.rollback()
        finally:
            conn.close()
    
    def print_table_results(self, results: Dict[str, Dict[str, Any]], top_n: Optional[int] = None):
        """Print results in a formatted table."""
        # Sort players by total performance (batting + bowling PRS)
        sorted_players = self._sort_players_by_performance(results)
        
        if top_n:
            sorted_players = sorted_players[:top_n]
        
        # Print header
        print("=" * 80)
        print("PRESSURE RESISTANCE SCORE (PRS) ANALYSIS")
        print("=" * 80)
        print(f"{'Name':<25} {'Batting PRS':<12} {'Bowling PRS':<12} {'Bat Balls':<10} {'Bowl Balls':<10}")
        print("-" * 80)
        
        for player_name, stats in sorted_players:
            data = []

            batting_prs = f"{stats['batting_prs']:.1f}" if stats['batting_prs'] > 0 else "N/A"
            bowling_prs = f"{stats['bowling_prs']:.1f}" if stats['bowling_prs'] > 0 else "N/A"
            
            data.append(player_name)
            data.append(batting_prs)
            data.append(bowling_prs)
            data.append(f"{stats['batting_deliveries']:<10}")
            data.append(f"{stats['bowling_deliveries']:<10}")

            ResultsFormatter.add_data(data)

            print(f"{player_name:<25} {batting_prs:<12} {bowling_prs:<12} "
                  f"{stats['batting_deliveries']:<10} {stats['bowling_deliveries']:<10}")
        
        print("-" * 80)
        print(f"Total players analyzed: {len(results)}")
        
        if top_n:
            print(f"Showing top {min(top_n, len(results))} performers")
    
    def print_detailed_results(self, results: Dict[str, Dict[str, Any]], 
                             top_n: Optional[int] = None, include_match_details: bool = False):
        """Print detailed results with additional statistics."""
        sorted_players = self._sort_players_by_performance(results)
        
        if top_n:
            sorted_players = sorted_players[:top_n]
        
        print("=" * 100)
        print("DETAILED PRESSURE RESISTANCE SCORE (PRS) ANALYSIS")
        print("=" * 100)
        
        for i, (player_name, stats) in enumerate(sorted_players, 1):
            print(f"\n{i}. {player_name}")
            print("-" * 50)
            
            # Batting stats
            if stats['batting_deliveries'] > 0:
                print(f"  Batting PRS: {stats['batting_prs']:.1f}")
                print(f"  Batting deliveries: {stats['batting_deliveries']}")
            else:
                print("  Batting: No data")
            
            # Bowling stats
            if stats['bowling_deliveries'] > 0:
                print(f"  Bowling PRS: {stats['bowling_prs']:.1f}")
                print(f"  Bowling deliveries: {stats['bowling_deliveries']}")
            else:
                print("  Bowling: No data")
            
            print(f"  Total deliveries: {stats['total_deliveries']}")
            
            # Overall assessment
            overall_score = (stats['batting_prs'] + stats['bowling_prs']) / 2
            print(f"  Overall PRS: {overall_score:.1f}")
            print(f"  Performance level: {self._get_performance_level(overall_score)}")
    
    def print_json_results(self, results: Dict[str, Dict[str, Any]]):
        """Print results in JSON format."""
        print(json.dumps(results, indent=2))
    
    def _sort_players_by_performance(self, results: Dict[str, Dict[str, Any]]) -> List[tuple]:
        """Sort players by their overall performance."""
        def sort_key(item):
            _, stats = item
            # Combine batting and bowling PRS, giving equal weight
            batting_score = stats['batting_prs'] if stats['batting_deliveries'] > 0 else 0
            bowling_score = stats['bowling_prs'] if stats['bowling_deliveries'] > 0 else 0
            
            # Weight by the number of deliveries to favor players with more data
            total_deliveries = stats['total_deliveries']
            weighted_score = (batting_score + bowling_score) * (1 + min(total_deliveries / 100, 1))
            
            return weighted_score
        
        return sorted(results.items(), key=sort_key, reverse=True)
    
    def _get_performance_level(self, prs_score: float) -> str:
        """Get performance level description based on PRS score."""
        if prs_score >= 80:
            return "Elite"
        elif prs_score >= 70:
            return "Excellent"
        elif prs_score >= 60:
            return "Good"
        elif prs_score >= 50:
            return "Average"
        else:
            return "Below Average"
    
    def print_top_performers(self, results: Dict[str, Dict[str, Any]], category: str = "overall"):
        """Print top 5 performers in a specific category."""
        if category == "batting":
            sorted_players = sorted(
                [(name, stats) for name, stats in results.items() if stats['batting_deliveries'] > 0],
                key=lambda x: x[1]['batting_prs'], reverse=True
            )[:5]
            print("\nTOP 5 BATTING PRESSURE PERFORMERS:")
            print("-" * 40)
            for i, (name, stats) in enumerate(sorted_players, 1):
                print(f"{i}. {name}: {stats['batting_prs']:.1f}")
        
        elif category == "bowling":
            sorted_players = sorted(
                [(name, stats) for name, stats in results.items() if stats['bowling_deliveries'] > 0],
                key=lambda x: x[1]['bowling_prs'], reverse=True
            )[:5]
            print("\nTOP 5 BOWLING PRESSURE PERFORMERS:")
            print("-" * 40)
            for i, (name, stats) in enumerate(sorted_players, 1):
                print(f"{i}. {name}: {stats['bowling_prs']:.1f}")
        
        else:  # overall
            sorted_players = self._sort_players_by_performance(results)[:5]
            print("\nTOP 5 OVERALL PRESSURE PERFORMERS:")
            print("-" * 40)
            for i, (name, stats) in enumerate(sorted_players, 1):
                overall = (stats['batting_prs'] + stats['bowling_prs']) / 2
                print(f"{i}. {name}: {overall:.1f} (B:{stats['batting_prs']:.1f}, Bo:{stats['bowling_prs']:.1f})")