#!/usr/bin/env python3
"""
Simple validation script for test_message_service.py structure.
Does not require full dependencies, just validates test structure.
"""
import ast
import sys


def validate_test_file(filepath):
    """Validate the test file has correct structure."""
    print(f"🔍 Validating {filepath}...")
    print()

    with open(filepath, 'r') as f:
        content = f.read()

    # Parse the AST
    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False

    # Count test classes and methods
    test_classes = []
    test_methods = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith('Test'):
                test_classes.append(node.name)
                # Count test methods in this class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_methods.append(f"{node.name}.{item.name}")

    print(f"✅ Found {len(test_classes)} test classes:")
    for cls in test_classes:
        print(f"   - {cls}")
    print()

    print(f"✅ Found {len(test_methods)} test methods:")
    for method in test_methods:
        print(f"   - {method}")
    print()

    # Verify key imports exist
    required_imports = [
        'pytest',
        'BaseMessageProvider',
        'CommonMessages',
        'LucienVoiceService',
        'ServiceContainer',
    ]

    found_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    found_imports.add(alias.name)
            else:
                for alias in node.names:
                    found_imports.add(alias.name)

    print("✅ Validating imports:")
    all_imports_ok = True
    for imp in required_imports:
        if imp in found_imports:
            print(f"   ✓ {imp}")
        else:
            print(f"   ✗ {imp} - MISSING")
            all_imports_ok = False
    print()

    # Verify test content patterns
    print("✅ Validating test content patterns:")

    patterns = {
        'Lucien emoji': '🎩',
        'HTML bold tags': '<b>',
        'HTML italic tags': '<i>',
        'Diana mentions': 'Diana',
        'No tutear check': 'tutear',
        'Technical jargon check': 'technical',
    }

    all_patterns_ok = True
    for pattern_name, pattern in patterns.items():
        if pattern in content:
            print(f"   ✓ {pattern_name} test present")
        else:
            print(f"   ✗ {pattern_name} test MISSING")
            all_patterns_ok = False
    print()

    # Summary
    print("=" * 50)
    if all_imports_ok and all_patterns_ok and len(test_methods) >= 27:
        print(f"✅ VALIDATION PASSED")
        print(f"   - {len(test_classes)} test classes")
        print(f"   - {len(test_methods)} test methods")
        print(f"   - All required imports present")
        print(f"   - All content patterns present")
        return True
    else:
        print(f"⚠️  VALIDATION WARNINGS:")
        if not all_imports_ok:
            print(f"   - Some imports missing")
        if not all_patterns_ok:
            print(f"   - Some content patterns missing")
        if len(test_methods) < 27:
            print(f"   - Expected at least 27 tests, found {len(test_methods)}")
        return False


if __name__ == '__main__':
    result = validate_test_file('tests/test_message_service.py')
    sys.exit(0 if result else 1)
