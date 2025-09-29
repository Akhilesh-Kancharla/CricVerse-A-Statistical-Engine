#!/usr/bin/env python3
"""
Cricket Pressure Resistance Score (PRS) Analyzer
Analyzes ball-by-ball cricket match data to compute pressure resistance scores for players.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List
from Package.cricket_analyzer import CricketAnalyzer


def find_yaml_files(directory: str) -> List[str]:
    """Find all YAML files in the given directory."""
    yaml_files = []
    path = Path(directory)
    
    if path.is_file() and path.suffix.lower() in ['.yaml', '.yml']:
        return [str(path)]
    
    if path.is_dir():
        for file_path in path.rglob('*.y*ml'):
            yaml_files.append(str(file_path))
    
    return yaml_files


def main():
    """Main entry point for the cricket PRS analyzer."""
    parser = argparse.ArgumentParser(
        description='Analyze cricket match data to compute Pressure Resistance Scores'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to YAML file or directory containing YAML files (default: current directory)'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'detailed', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--top',
        type=int,
        help='Show only top N performers'
    )
    parser.add_argument(
        '--match-details',
        action='store_true',
        help='Include match-by-match breakdown'
    )
    
    args = parser.parse_args()
    args.path = "Matches"
    # Find YAML files
    yaml_files = find_yaml_files(args.path)
    
    if not yaml_files:
        print(f"No YAML files found in: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(yaml_files)} YAML files to analyze...", file=sys.stderr)
    
    # Initialize analyzer
    analyzer = CricketAnalyzer()
    
    # Process all files
    for yaml_file in yaml_files:
        try:
            analyzer.process_match_file(yaml_file)
            print(f"Processed: {yaml_file}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {yaml_file}: {e}", file=sys.stderr)
            continue
    
    # Generate and display results
    try:
        analyzer.display_results(
            format_type=args.format,
            top_n=args.top,
            include_match_details=args.match_details
        )
    except Exception as e:
        print(f"Error generating results: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()