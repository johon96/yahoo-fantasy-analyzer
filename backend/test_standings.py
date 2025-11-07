#!/usr/bin/env python3
"""Test script to verify standings export with managers."""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from export_players import export_standings_to_csv

if __name__ == "__main__":
    league_key = "465.l.34948"
    output_file = "test_standings.csv"
    
    if len(sys.argv) > 1:
        league_key = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print(f"Testing standings export for league: {league_key}")
    print(f"Output file: {output_file}\n")
    
    export_standings_to_csv(league_key, output_file)
    
    # Read and display the CSV
    print("\n" + "="*60)
    print("CSV Contents:")
    print("="*60)
    with open(output_file, 'r', encoding='utf-8-sig') as f:
        print(f.read())

