#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Excel Data Cleaning Skill - run.py
Main entry point for the excel-data-cleaning skill.
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


def load_spec(config_path):
    """Load the cleaning specification from a JSON config file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_path}: {e}")


def match_trigger(filename, trigger_patterns):
    """Check if a filename matches any of the trigger patterns."""
    if not trigger_patterns:
        return True
    name = Path(filename).name.lower()
    for pattern in trigger_patterns:
        if pattern.lower() in name:
            return True
    return False


def clean_csv_file(input_path, output_path, spec):
    """Clean a CSV file according to the spec."""
    try:
        # Read spec details
        delimiter = spec.get('delimiter', ',')
        encoding = spec.get('encoding', 'utf-8')
        remove_duplicates = spec.get('remove_duplicates', False)
        drop_columns = spec.get('drop_columns', [])
        rename_columns = spec.get('rename_columns', {})
        fillna_value = spec.get('fillna_value', '')
        strip_whitespace = spec.get('strip_whitespace', False)
        date_columns = spec.get('date_columns', [])
        date_format = spec.get('date_format', '%Y-%m-%d')

        rows = []
        fieldnames = []
        try:
            with open(input_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = reader.fieldnames
                for row in reader:
                    rows.append(row)
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        # Process rows
        processed_rows = []
        seen = set()
        for row in rows:
            # Skip empty rows
            if not row or all(v is None or v == '' for v in row.values()):
                continue

            # Strip whitespace if requested
            if strip_whitespace:
                row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

            # Remove duplicates if requested
            if remove_duplicates:
                row_key = tuple(sorted(row.items()))
                if row_key in seen:
                    continue
                seen.add(row_key)

            # Drop columns
            for col in drop_columns:
                if col in row:
                    del row[col]

            # Rename columns
            for old_name, new_name in rename_columns.items():
                if old_name in row:
                    row[new_name] = row.pop(old_name)

            # Fill NA values
            for col in fieldnames:
                if col in row and (row[col] is None or row[col] == ''):
                    row[col] = fillna_value

            # Format date columns
            for col in date_columns:
                if col in row and row[col]:
                    try:
                        # Try to parse and reformat
                        dt = datetime.strptime(row[col], '%Y-%m-%d')
                        row[col] = dt.strftime(date_format)
                    except (ValueError, TypeError):
                        # Keep original if parsing fails
                        pass

            processed_rows.append(row)

        # Write output atomically
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(output_path) or '.', suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w', encoding=encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(processed_rows)
            os.replace(temp_path, output_path)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

        return len(processed_rows), len(rows) - len(processed_rows), 0
    except Exception as e:
        return 0, 0, 1


def process_file(input_path, output_path, spec):
    """Process a single file according to the spec."""
    try:
        # Check if file exists
        if not os.path.exists(input_path):
            return {'file': input_path, 'status': 'failed', 'error': 'File not found'}

        # Check file extension
        ext = Path(input_path).suffix.lower()
        if ext not in ['.csv', '.txt']:
            return {'file': input_path, 'status': 'failed', 'error': f'Unsupported file type: {ext}'}

        # Process based on file type
        if ext in ['.csv', '.txt']:
            success, skipped, failed = clean_csv_file(input_path, output_path, spec)
            if failed > 0:
                return {'file': input_path, 'status': 'failed', 'error': 'Processing failed'}
            return {'file': input_path, 'status': 'success', 'processed': success, 'skipped': skipped}
        else:
            return {'file': input_path, 'status': 'failed', 'error': 'Unsupported file type'}

    except Exception as e:
        return {'file': input_path, 'status': 'failed', 'error': str(e)}


def run_selftest():
    """Run self-test to verify core functionality."""
    print("Running self-test...")
    
    # Create test data
    test_dir = tempfile.mkdtemp()
    test_input = os.path.join(test_dir, 'test_input.csv')
    test_output = os.path.join(test_dir, 'test_output.csv')
    
    # Create test CSV
    with open(test_input, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'age', 'email'])
        writer.writerow(['Alice', '30', 'alice@example.com'])
        writer.writerow(['Bob', '25', 'bob@example.com'])
        writer.writerow(['Alice', '30', 'alice@example.com'])  # duplicate
    
    # Test spec
    spec = {
        'delimiter': ',',
        'encoding': 'utf-8',
        'remove_duplicates': True,
        'strip_whitespace': True,
        'fillna_value': 'N/A',
        'date_columns': [],
        'date_format': '%Y-%m-%d'
    }
    
    # Test clean_csv_file
    success, skipped, failed = clean_csv_file(test_input, test_output, spec)
    assert success == 2, f"Expected 2 rows, got {success}"
    assert skipped == 1, f"Expected 1 skipped, got {skipped}"
    assert failed == 0, f"Expected 0 failed, got {failed}"
    
    # Verify output
    with open(test_output, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2, f"Expected 2 rows in output, got {len(rows)}"
        assert rows[0]['name'] == 'Alice', "First row should be Alice"
        assert rows[1]['name'] == 'Bob', "Second row should be Bob"
    
    # Test match_trigger
    assert match_trigger('test.csv', ['test']) == True
    assert match_trigger('other.csv', ['test']) == False
    assert match_trigger('any.csv', []) == True
    
    # Test load_spec with invalid file
    try:
        load_spec('/nonexistent/path/config.json')
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass
    
    # Test process_file with nonexistent file
    result = process_file('/nonexistent/file.csv', '/tmp/out.csv', spec)
    assert result['status'] == 'failed', "Should have failed for nonexistent file"
    
    # Test process_file with unsupported extension
    result = process_file('test.xlsx', 'test_out.xlsx', spec)
    assert result['status'] == 'failed', "Should have failed for unsupported extension"
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)
    
    print("Self-test passed!")
    return 0


def main():
    parser = argparse.ArgumentParser(description='Excel Data Cleaning Skill')
    parser.add_argument('--input', '-i', help='Input file or directory')
    parser.add_argument('--output', '-o', help='Output file or directory')
    parser.add_argument('--config', '-c', help='Config file (JSON)')
    parser.add_argument('--selftest', action='store_true', help='Run self-test')
    parser.add_argument('--trigger', help='Trigger pattern for file selection')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    if not args.input:
        print("Error: --input is required (or use --selftest)", file=sys.stderr)
        return 1
    
    # Load config
    spec = {}
    if args.config:
        try:
            spec = load_spec(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            return 1
    
    # Process input
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    results = []
    total_success = 0
    total_failed = 0
    total_skipped = 0
    
    if input_path.is_dir():
        # Process all files in directory
        for file_path in input_path.iterdir():
            if file_path.is_file():
                if args.trigger and not match_trigger(file_path.name, [args.trigger]):
                    continue
                
                out_file = output_path / f"{file_path.stem}_out{file_path.suffix}" if output_path else file_path.with_name(f"{file_path.stem}_out{file_path.suffix}")
                result = process_file(str(file_path), str(out_file), spec)
                results.append(result)
                
                if result['status'] == 'success':
                    total_success += 1
                    total_skipped += result.get('skipped', 0)
                else:
                    total_failed += 1
    else:
        # Process single file
        out_file = output_path if output_path else input_path.with_name(f"{input_path.stem}_out{input_path.suffix}")
        result = process_file(str(input_path), str(out_file), spec)
        results.append(result)
        
        if result['status'] == 'success':
            total_success += 1
            total_skipped += result.get('skipped', 0)
        else:
            total_failed += 1
    
    # Print summary
    print(f"\nProcessing Summary:")
    print(f"  Total files: {len(results)}")
    print(f"  Success: {total_success}")
    print(f"  Skipped: {total_skipped}")
    print(f"  Failed: {total_failed}")
    
    if args.verbose:
        print("\nDetailed Results:")
        for result in results:
            print(f"  {result['file']}: {result['status']}")
            if result['status'] == 'failed':
                print(f"    Error: {result.get('error', 'Unknown error')}")
    
    # Print failure details
    failed_results = [r for r in results if r['status'] == 'failed']
    if failed_results:
        print("\nFailed Files:")
        for result in failed_results:
            print(f"  {result['file']}: {result.get('error', 'Unknown error')}")
    
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
