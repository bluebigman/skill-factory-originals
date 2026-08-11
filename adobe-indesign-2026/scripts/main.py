#!/usr/bin/env python3
"""Template rendering engine with dry-run support."""

import sys
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

class TemplateEngine:
    """Simple template engine supporting variables, conditionals, loops, and filters."""
    
    def __init__(self):
        self.pattern = r'\{\{\s*([^}]+?)\s*\}\}'
        self.condition_pattern = r'\{%\s*if\s+([^%]+?)\s*%\}(.*?)\{%\s*endif\s*%\}'
        self.loop_pattern = r'\{%\s*for\s+(\w+)\s+in\s+([^%]+?)\s*%\}(.*?)\{%\s*endfor\s*%\}'
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render template with given context."""
        # Process loops first
        result = self._process_loops(template, context)
        # Process conditionals
        result = self._process_conditionals(result, context)
        # Process variables
        result = self._process_variables(result, context)
        return result
    
    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """Process for loops in template."""
        def replace_loop(match):
            var_name = match.group(1)
            iterable_name = match.group(2).strip()
            body = match.group(3)
            
            if iterable_name not in context:
                return ''
            
            iterable = context[iterable_name]
            if not isinstance(iterable, (list, tuple)):
                return ''
            
            result = []
            for item in iterable:
                local_context = dict(context)
                local_context[var_name] = item
                result.append(self._process_variables(body, local_context))
            return ''.join(result)
        
        return re.sub(self.loop_pattern, replace_loop, template, flags=re.DOTALL)
    
    def _process_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        """Process if conditionals in template."""
        def replace_condition(match):
            condition = match.group(1).strip()
            body = match.group(2)
            
            # Evaluate condition
            if condition in context:
                value = context[condition]
                if value:
                    return body
            return ''
        
        return re.sub(self.condition_pattern, replace_condition, template, flags=re.DOTALL)
    
    def _process_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Process variable substitutions with filters."""
        def replace_var(match):
            expr = match.group(1).strip()
            
            # Check for filters
            parts = expr.split('|')
            var_name = parts[0].strip()
            
            if var_name not in context:
                return ''
            
            value = context[var_name]
            
            # Apply filters
            for filter_part in parts[1:]:
                filter_name = filter_part.strip()
                if filter_name == 'upper':
                    value = str(value).upper()
                elif filter_name == 'lower':
                    value = str(value).lower()
                elif filter_name == 'trim':
                    value = str(value).strip()
                elif filter_name == 'length':
                    value = len(value)
            
            return str(value)
        
        return re.sub(self.pattern, replace_var, template)


def render_file(
    template_file: str,
    output_file: str,
    context: Optional[Dict[str, Any]] = None,
    dry_run: bool = False
) -> None:
    """
    Render a template file with given context.
    
    Args:
        template_file: Path to template file
        output_file: Path to output file
        context: Dictionary of variables for rendering
        dry_run: If True, print rendered content instead of writing
    """
    if context is None:
        context = {}
    
    # Read template
    template_path = Path(template_file)
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")
    
    template_content = template_path.read_text(encoding='utf-8')
    
    # Render template
    engine = TemplateEngine()
    rendered_content = engine.render(template_content, context)
    
    if dry_run:
        # Print rendered content for preview
        print(rendered_content)
    else:
        # Write to output file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_content, encoding='utf-8')


def selftest() -> bool:
    """Run self-tests to verify template engine functionality."""
    engine = TemplateEngine()
    
    # Test 1: Basic variable substitution
    template = "Hello, {{ name }}!"
    result = engine.render(template, {"name": "World"})
    assert result == "Hello, World!", f"Basic variable substitution failed: {result}"
    assert "{{" not in result and "}}" not in result, "Template markers not fully processed"
    
    # Test 2: Multiple variables
    template = "{{ first }} {{ second }}"
    result = engine.render(template, {"first": "Hello", "second": "World"})
    assert result == "Hello World", f"Multiple variable substitution failed: {result}"
    
    # Test 3: Missing variables
    template = "Value: {{ missing_var }}"
    result = engine.render(template, {})
    assert result == "Value: ", f"Missing variable should return empty: {result}"
    
    # Test 4: Conditionals
    template = "{% if show %}Visible{% endif %}"
    result = engine.render(template, {"show": True})
    assert result == "Visible", f"True condition failed: {result}"
    
    result = engine.render(template, {"show": False})
    assert result == "", f"False condition should be empty: {result}"
    
    # Test 5: Loops
    template = "{% for item in items %}{{ item }},{% endfor %}"
    result = engine.render(template, {"items": ["a", "b", "c"]})
    assert result == "a,b,c,", f"Loop failed: {result}"
    
    # Test 6: Filters
    template = "{{ name|upper }}"
    result = engine.render(template, {"name": "hello"})
    assert result == "HELLO", f"Upper filter failed: {result}"
    
    template = "{{ name|lower }}"
    result = engine.render(template, {"name": "HELLO"})
    assert result == "hello", f"Lower filter failed: {result}"
    
    # Test 7: dry-run mode
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = os.path.join(tmpdir, "test.tpl")
        output_file = os.path.join(tmpdir, "output.txt")
        
        with open(template_file, 'w') as f:
            f.write("Hello, {{ name }}!")
        
        # Test dry_run=True (should not create output file)
        render_file(template_file, output_file, {"name": "Test"}, dry_run=True)
        assert not os.path.exists(output_file), "dry_run should not create output file"
        
        # Test normal rendering
        render_file(template_file, output_file, {"name": "Test"})
        assert os.path.exists(output_file), "Normal rendering should create output file"
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "Hello, Test!", f"File content mismatch: {content}"
    
    return True


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        try:
            selftest()
            print("All tests passed!")
            return 0
        except AssertionError as e:
            print(f"Test failed: {e}")
            return 1
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python main.py <template_file> <output_file> [--context JSON] [--dry-run]")
        return 1
    
    template_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Parse optional arguments
    context = {}
    dry_run = False
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--context" and i + 1 < len(sys.argv):
            try:
                context = json.loads(sys.argv[i + 1])
                i += 2
            except json.JSONDecodeError:
                print("Invalid JSON context")
                return 1
        elif sys.argv[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1
    
    try:
        render_file(template_file, output_file, context, dry_run)
        if dry_run:
            print("Dry run completed (no file written)")
        else:
            print(f"Template rendered to {output_file}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
