#!/usr/bin/env python3
"""Train ticket query tool with offline self-test."""

import argparse
import json
import sys
import re
from datetime import datetime, timedelta


def parse_train_info(raw_text):
    """Parse train information from raw text lines."""
    trains = []
    lines = raw_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Expected format: train_no|from|to|date|departure|arrival|duration|seat_type|price
        parts = line.split('|')
        if len(parts) >= 9:
            train = {
                'train_no': parts[0].strip(),
                'from': parts[1].strip(),
                'to': parts[2].strip(),
                'date': parts[3].strip(),
                'departure': parts[4].strip(),
                'arrival': parts[5].strip(),
                'duration': parts[6].strip(),
                'seat_type': parts[7].strip(),
                'price': float(parts[8].strip())
            }
            trains.append(train)
    return trains


def filter_trains(trains, from_station=None, to_station=None, date=None, seat_type=None):
    """Filter trains based on criteria."""
    result = []
    for train in trains:
        if from_station and train['from'] != from_station:
            continue
        if to_station and train['to'] != to_station:
            continue
        if date and train['date'] != date:
            continue
        if seat_type and train['seat_type'] != seat_type:
            continue
        result.append(train)
    return result


def sort_trains(trains, sort_by='price', reverse=False):
    """Sort trains by specified field."""
    if sort_by not in ['price', 'departure', 'duration']:
        sort_by = 'price'
    return sorted(trains, key=lambda x: x[sort_by], reverse=reverse)


def get_available_trains(data, from_station, to_station, date, seat_type=None):
    """Main query function."""
    trains = parse_train_info(data)
    filtered = filter_trains(trains, from_station, to_station, date, seat_type)
    return sort_trains(filtered)


def generate_test_data():
    """Generate sample train data for testing."""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    data = f"""G101|北京|上海|{today}|08:00|13:30|05:30|二等座|553
G101|北京|上海|{today}|08:00|13:30|05:30|一等座|933
G102|北京|上海|{today}|09:00|14:30|05:30|二等座|553
G103|北京|上海|{tomorrow}|10:00|15:30|05:30|二等座|553
D301|北京|广州|{today}|07:30|20:30|13:00|二等座|862
D301|北京|广州|{today}|07:30|20:30|13:00|一等座|1379
K529|北京|成都|{today}|12:00|次日08:30|20:30|硬卧|456
K529|北京|成都|{today}|12:00|次日08:30|20:30|软卧|756"""
    return data


def run_selftest():
    """Run offline self-test."""
    print("Running self-test...")
    
    # Test 1: Parse train info
    test_data = generate_test_data()
    trains = parse_train_info(test_data)
    assert len(trains) == 8, f"Expected 8 trains, got {len(trains)}"
    print("✓ Parse train info: PASS")
    
    # Test 2: Filter by from/to
    filtered = filter_trains(trains, from_station="北京", to_station="上海")
    assert len(filtered) == 6, f"Expected 6 trains, got {len(filtered)}"
    print("✓ Filter by from/to: PASS")
    
    # Test 3: Filter by date
    today = datetime.now().strftime('%Y-%m-%d')
    filtered = filter_trains(trains, date=today)
    assert len(filtered) == 6, f"Expected 6 trains, got {len(filtered)}"
    print("✓ Filter by date: PASS")
    
    # Test 4: Filter by seat type
    filtered = filter_trains(trains, seat_type="二等座")
    assert len(filtered) == 5, f"Expected 5 trains, got {len(filtered)}"
    print("✓ Filter by seat type: PASS")
    
    # Test 5: Sort by price
    sorted_trains = sort_trains(trains, sort_by='price')
    assert sorted_trains[0]['price'] <= sorted_trains[-1]['price'], "Sort by price failed"
    print("✓ Sort by price: PASS")
    
    # Test 6: Combined query
    result = get_available_trains(test_data, "北京", "上海", today, "二等座")
    assert len(result) == 3, f"Expected 3 trains, got {len(result)}"
    assert all(t['price'] == 553 for t in result), "All should be 553 yuan"
    print("✓ Combined query: PASS")
    
    # Test 7: Sort by departure time
    sorted_trains = sort_trains(trains, sort_by='departure')
    assert sorted_trains[0]['departure'] <= sorted_trains[-1]['departure'], "Sort by departure failed"
    print("✓ Sort by departure: PASS")
    
    print("\nAll self-tests passed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(description='Train ticket query tool')
    parser.add_argument('--selftest', action='store_true', help='Run offline self-test')
    parser.add_argument('--from', dest='from_station', help='Departure station')
    parser.add_argument('--to', dest='to_station', help='Arrival station')
    parser.add_argument('--date', help='Travel date (YYYY-MM-DD)')
    parser.add_argument('--seat', dest='seat_type', help='Seat type (e.g., 二等座)')
    parser.add_argument('--sort', default='price', choices=['price', 'departure', 'duration'],
                       help='Sort by field')
    parser.add_argument('--reverse', action='store_true', help='Reverse sort order')
    parser.add_argument('--data', help='Path to data file (optional, uses sample data if not provided)')
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    # Get data source
    if args.data:
        try:
            with open(args.data, 'r', encoding='utf-8') as f:
                data = f.read()
        except FileNotFoundError:
            print(f"Error: Data file {args.data} not found")
            return 1
    else:
        data = generate_test_data()
        print("Using sample data (no --data file provided)")
    
    # Perform query
    if not args.from_station or not args.to_station or not args.date:
        print("Error: --from, --to, and --date are required for queries")
        print("Use --selftest for offline testing")
        return 1
    
    try:
        trains = get_available_trains(data, args.from_station, args.to_station, args.date, args.seat_type)
        if not trains:
            print("No trains found matching your criteria")
            return 0
        
        print(f"\nFound {len(trains)} trains:")
        print("-" * 80)
        for train in trains:
            print(f"{train['train_no']} | {train['from']} -> {train['to']} | {train['date']} | "
                  f"{train['departure']} - {train['arrival']} | {train['duration']} | "
                  f"{train['seat_type']} | ¥{train['price']:.0f}")
        return 0
    except Exception as e:
        print(f"Error during query: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
