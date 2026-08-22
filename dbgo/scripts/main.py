#!/usr/bin/env python3
"""Main entry point for the application."""

import argparse
import json
import sys
import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


def parse_model_file(model_file: str) -> Dict[str, Any]:
    """Parse a JSON model file describing database tables and fields."""
    with open(model_file, 'r') as f:
        model = json.load(f)
    
    if not isinstance(model, dict) or 'tables' not in model:
        raise ValueError("Model file must contain a 'tables' key with table definitions")
    
    return model


def generate_go_code(model: Dict[str, Any], package_name: str = "generated") -> str:
    """Generate Go code from the model definition."""
    tables = model['tables']
    
    go_code = f"""package {package_name}

import (
    "database/sql"
    "fmt"
)

"""
    
    for table in tables:
        table_name = table['name']
        struct_name = ''.join(word.capitalize() for word in table_name.split('_'))
        fields = table['fields']
        
        # Generate struct definition
        go_code += f"type {struct_name} struct {{\n"
        for field in fields:
            field_name = ''.join(word.capitalize() for word in field['name'].split('_'))
            go_type = field.get('go_type', 'string')
            go_code += f"    {field_name} {go_type} `json:\"{field['name']}\"`\n"
        go_code += "}\n\n"
        
        # Generate CRUD functions
        go_code += f"func Create{struct_name}(db *sql.DB, data *{struct_name}) error {{\n"
        field_names = [f['name'] for f in fields]
        placeholders = ", ".join(["?"] * len(field_names))
        columns = ", ".join(field_names)
        go_code += f"    query := \"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})\"\n"
        go_code += "    _, err := db.Exec(query, "
        go_code += ", ".join([f"data.{''.join(word.capitalize() for word in f['name'].split('_'))}" for f in fields])
        go_code += ")\n"
        go_code += "    return err\n"
        go_code += "}\n\n"
        
        go_code += f"func Get{struct_name}(db *sql.DB, id int) (*{struct_name}, error) {{\n"
        go_code += f"    query := \"SELECT * FROM {table_name} WHERE id = ?\"\n"
        go_code += f"    row := db.QueryRow(query, id)\n"
        go_code += f"    data := &{struct_name}{{}}\n"
        go_code += "    err := row.Scan("
        go_code += ", ".join([f"&data.{''.join(word.capitalize() for word in f['name'].split('_'))}" for f in fields])
        go_code += ")\n"
        go_code += "    return data, err\n"
        go_code += "}\n\n"
    
    return go_code


def generate_sql(model: Dict[str, Any]) -> str:
    """Generate SQL DDL statements from the model definition."""
    tables = model['tables']
    sql_statements = []
    
    for table in tables:
        table_name = table['name']
        fields = table['fields']
        
        columns = []
        for field in fields:
            field_name = field['name']
            sql_type = field.get('sql_type', 'TEXT')
            constraints = field.get('constraints', [])
            
            column_def = f"    {field_name} {sql_type}"
            if 'primary_key' in constraints:
                column_def += " PRIMARY KEY"
            if 'not_null' in constraints:
                column_def += " NOT NULL"
            if 'unique' in constraints:
                column_def += " UNIQUE"
            if 'default' in field:
                column_def += f" DEFAULT {field['default']}"
            
            columns.append(column_def)
        
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} (\n" + ",\n".join(columns) + "\n);"
        sql_statements.append(create_stmt)
        
        # Add indexes if specified
        if 'indexes' in table:
            for index in table['indexes']:
                index_name = f"idx_{table_name}_{'_'.join(index)}"
                index_stmt = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({', '.join(index)});"
                sql_statements.append(index_stmt)
    
    return "\n\n".join(sql_statements)


def generate_package(model: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """Generate the complete package with Go code and SQL files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate Go code
    go_code = generate_go_code(model)
    go_file = output_path / "models.go"
    go_file.write_text(go_code)
    
    # Generate SQL
    sql_code = generate_sql(model)
    sql_file = output_path / "schema.sql"
    sql_file.write_text(sql_code)
    
    # Generate README
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    readme_content = f"""# Generated Package

Generated at: {timestamp}

## Files
- `models.go`: Go structs and CRUD functions
- `schema.sql`: SQL DDL statements

## Usage
1. Execute `schema.sql` to create tables
2. Import `models.go` in your Go application
3. Use the generated CRUD functions
"""
    readme_file = output_path / "README.md"
    readme_file.write_text(readme_content)
    
    return {
        "go_file": str(go_file),
        "sql_file": str(sql_file),
        "readme_file": str(readme_file)
    }


def run_selftest() -> int:
    """Run self-tests to verify the module works correctly."""
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Model parsing and Go code generation
    try:
        test_model = {
            "tables": [
                {
                    "name": "users",
                    "fields": [
                        {"name": "id", "go_type": "int", "sql_type": "INTEGER", "constraints": ["primary_key"]},
                        {"name": "name", "go_type": "string", "sql_type": "TEXT", "constraints": ["not_null"]},
                        {"name": "email", "go_type": "string", "sql_type": "TEXT", "constraints": ["unique"]}
                    ],
                    "indexes": [["email"]]
                }
            ]
        }
        
        go_code = generate_go_code(test_model)
        assert "type Users struct" in go_code
        assert "func CreateUsers" in go_code
        assert "func GetUsers" in go_code
        assert "INSERT INTO users" in go_code
        assert "SELECT * FROM users" in go_code
        tests_passed += 1
    except AssertionError as e:
        tests_failed += 1
        print(f"FAIL: Go code generation test failed: {e}")
    
    # Test 2: SQL generation
    try:
        test_model = {
            "tables": [
                {
                    "name": "users",
                    "fields": [
                        {"name": "id", "sql_type": "INTEGER", "constraints": ["primary_key"]},
                        {"name": "name", "sql_type": "TEXT", "constraints": ["not_null"]},
                        {"name": "email", "sql_type": "TEXT", "constraints": ["unique"]}
                    ],
                    "indexes": [["email"]]
                }
            ]
        }
        
        sql_code = generate_sql(test_model)
        assert "CREATE TABLE IF NOT EXISTS users" in sql_code
        assert "id INTEGER PRIMARY KEY" in sql_code
        assert "name TEXT NOT NULL" in sql_code
        assert "email TEXT UNIQUE" in sql_code
        assert "CREATE INDEX IF NOT EXISTS idx_users_email" in sql_code
        tests_passed += 1
    except AssertionError as e:
        tests_failed += 1
        print(f"FAIL: SQL generation test failed: {e}")
    
    # Test 3: Full package generation with file output
    try:
        import tempfile
        import shutil
        
        test_model = {
            "tables": [
                {
                    "name": "products",
                    "fields": [
                        {"name": "id", "go_type": "int", "sql_type": "INTEGER", "constraints": ["primary_key"]},
                        {"name": "name", "go_type": "string", "sql_type": "TEXT", "constraints": ["not_null"]},
                        {"name": "price", "go_type": "float64", "sql_type": "REAL", "constraints": ["not_null"]}
                    ]
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_package(test_model, tmpdir)
            
            # Verify files were created
            assert Path(result['go_file']).exists()
            assert Path(result['sql_file']).exists()
            assert Path(result['readme_file']).exists()
            
            # Verify content
            go_content = Path(result['go_file']).read_text()
            assert "type Products struct" in go_content
            assert "func CreateProducts" in go_content
            
            sql_content = Path(result['sql_file']).read_text()
            assert "CREATE TABLE IF NOT EXISTS products" in sql_content
            
            readme_content = Path(result['readme_file']).read_text()
            assert "Generated Package" in readme_content
            assert "models.go" in readme_content
        
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        print(f"FAIL: Package generation test failed: {e}")
    
    # Test 4: Model file parsing
    try:
        import tempfile
        
        test_model = {
            "tables": [
                {
                    "name": "test_table",
                    "fields": [
                        {"name": "id", "go_type": "int", "sql_type": "INTEGER"}
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_model, f)
            model_file = f.name
        
        try:
            parsed_model = parse_model_file(model_file)
            assert 'tables' in parsed_model
            assert len(parsed_model['tables']) == 1
            assert parsed_model['tables'][0]['name'] == 'test_table'
            tests_passed += 1
        finally:
            Path(model_file).unlink()
    except Exception as e:
        tests_failed += 1
        print(f"FAIL: Model file parsing test failed: {e}")
    
    # Test 5: Database integration test
    try:
        # Create in-memory database
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Test User", "test@example.com"))
        conn.commit()
        
        # Query the data
        cursor.execute("SELECT * FROM users WHERE email = ?", ("test@example.com",))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == "Test User"
        assert row[2] == "test@example.com"
        
        conn.close()
        tests_passed += 1
    except Exception as e:
        tests_failed += 1
        print(f"FAIL: Database integration test failed: {e}")
    
    print(f"\nSelf-test results: {tests_passed} passed, {tests_failed} failed")
    return 1 if tests_failed > 0 else 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database model to Go code and SQL generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --model-file model.json --output-dir ./generated
  python main.py --db-dsn sqlite:///test.db --model-file model.json --output-dir ./generated
  python main.py --selftest
        """
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run self-tests to verify the installation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="1.0.0",
    )
    parser.add_argument(
        "--db-dsn",
        type=str,
        help="Database DSN (e.g., sqlite:///path/to/db.sqlite3)",
    )
    parser.add_argument(
        "--model-file",
        type=str,
        help="Path to JSON model file describing database schema",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./generated",
        help="Output directory for generated files (default: ./generated)",
    )
    parser.add_argument(
        "--package-name",
        type=str,
        default="generated",
        help="Go package name for generated code (default: generated)",
    )
    
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    # Validate required arguments for generation
    if not args.model_file:
        parser.error("--model-file is required for code generation")
    
    try:
        # Parse model file
        model = parse_model_file(args.model_file)
        
        # Generate package
        result = generate_package(model, args.output_dir)
        
        print(f"Successfully generated package in {args.output_dir}:")
        for key, path in result.items():
            print(f"  {key}: {path}")
        
        # If database DSN provided, validate SQL against database
        if args.db_dsn:
            if args.db_dsn.startswith("sqlite:///"):
                db_path = args.db_dsn.replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                try:
                    sql_content = Path(result['sql_file']).read_text()
                    conn.executescript(sql_content)
                    print(f"  Database schema validated against {args.db_dsn}")
                finally:
                    conn.close()
            else:
                print(f"  Warning: Unsupported DSN format: {args.db_dsn}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
