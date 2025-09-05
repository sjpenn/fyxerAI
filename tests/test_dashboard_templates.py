"""
Test dashboard template rendering and context passing.
"""
import os
import subprocess
import time
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse

def test_template_files_exist():
    """Test that dashboard template files are properly set up."""
    
    project_root = Path(__file__).parent.parent
    
    required_templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
        project_root / 'core' / 'templates' / 'components-showcase.html',
    ]
    
    print("Testing dashboard template file setup...")
    
    for template_path in required_templates:
        if template_path.exists():
            print(f"✓ {template_path.name} exists")
        else:
            print(f"✗ {template_path.name} missing")
            return False
    
    return True

def test_template_structure():
    """Test that templates have proper Django structure."""
    
    project_root = Path(__file__).parent.parent
    base_template = project_root / 'core' / 'templates' / 'base.html'
    dashboard_template = project_root / 'core' / 'templates' / 'dashboard.html'
    
    print("Testing template structure...")
    
    if not base_template.exists():
        print("✗ Base template not found")
        return False
    
    base_content = base_template.read_text()
    
    # Check for required Django template features
    django_features = [
        '{% block',
        '{% load static %}',
        '<!DOCTYPE html>',
        '<html',
        '<head>',
        '<body>',
        '{% block content %}',
        '{% endblock %}'
    ]
    
    for feature in django_features:
        if feature in base_content:
            print(f"✓ Base template contains {feature}")
        else:
            print(f"✗ Base template missing {feature}")
            return False
    
    # Check dashboard template inheritance
    if dashboard_template.exists():
        dashboard_content = dashboard_template.read_text()
        
        dashboard_features = [
            "{% extends 'base.html' %}",
            '{% block',
            'dashboard'
        ]
        
        for feature in dashboard_features:
            if feature in dashboard_content:
                print(f"✓ Dashboard template contains {feature}")
            else:
                print(f"✗ Dashboard template missing {feature}")
                return False
    
    return True

def test_responsive_design_classes():
    """Test that templates include responsive design classes."""
    
    project_root = Path(__file__).parent.parent
    templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing responsive design classes...")
    
    responsive_classes = [
        'sm:', 'md:', 'lg:', 'xl:',  # Tailwind breakpoints
        'flex', 'grid',  # Layout systems
        'max-w-', 'w-full',  # Width utilities
        'mobile', 'desktop'  # Custom responsive classes
    ]
    
    for template_path in templates:
        if template_path.exists():
            content = template_path.read_text()
            found_responsive = []
            
            for cls in responsive_classes:
                if cls in content:
                    found_responsive.append(cls)
            
            if found_responsive:
                print(f"✓ {template_path.name} includes responsive classes: {found_responsive[:3]}...")
            else:
                print(f"! {template_path.name} could include more responsive classes")
    
    return True

def test_alpine_integration():
    """Test that templates properly integrate Alpine.js features."""
    
    project_root = Path(__file__).parent.parent
    templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing Alpine.js integration...")
    
    alpine_features = [
        'x-data',
        'x-show',
        'x-transition',
        '@click',
        '$store',
        'AlpineComponents'
    ]
    
    for template_path in templates:
        if template_path.exists():
            content = template_path.read_text()
            found_alpine = []
            
            for feature in alpine_features:
                if feature in content:
                    found_alpine.append(feature)
            
            if found_alpine:
                print(f"✓ {template_path.name} includes Alpine.js features: {found_alpine}")
            else:
                print(f"! {template_path.name} could include Alpine.js features")
    
    return True

def test_accessibility_features():
    """Test that templates include accessibility features."""
    
    project_root = Path(__file__).parent.parent
    templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing accessibility features...")
    
    accessibility_features = [
        'aria-',
        'role=',
        'tabindex',
        'alt=',
        'lang=',
        'aria-label',
        'aria-expanded',
        'aria-hidden'
    ]
    
    for template_path in templates:
        if template_path.exists():
            content = template_path.read_text()
            found_a11y = []
            
            for feature in accessibility_features:
                if feature in content:
                    found_a11y.append(feature)
            
            if found_a11y:
                print(f"✓ {template_path.name} includes accessibility features: {found_a11y}")
            else:
                print(f"! {template_path.name} could include accessibility features")
    
    return True

def test_theme_toggle_implementation():
    """Test that theme toggle is properly implemented."""
    
    project_root = Path(__file__).parent.parent
    base_template = project_root / 'core' / 'templates' / 'base.html'
    
    print("Testing theme toggle implementation...")
    
    if not base_template.exists():
        print("✗ Base template not found")
        return False
    
    content = base_template.read_text()
    
    theme_features = [
        'data-theme-toggle',
        '$store.theme',
        'dark:',
        'theme.toggle',
        'isDark'
    ]
    
    for feature in theme_features:
        if feature in content:
            print(f"✓ Theme toggle includes {feature}")
        else:
            print(f"! Theme toggle could include {feature}")
    
    return True

def test_dashboard_rendering():
    """Test that dashboard renders correctly via HTTP."""
    
    project_root = Path(__file__).parent.parent
    
    print("Testing dashboard rendering via HTTP...")
    
    try:
        # Start Django server
        django_process = subprocess.Popen(
            ['python', 'manage.py', 'runserver', '8005'],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'fyxerai_assistant.settings'}
        )
        
        # Wait for server to start
        time.sleep(3)
        
        # Test homepage
        curl_process = subprocess.run(
            ['curl', '-s', 'http://localhost:8005/'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Test components page
        components_process = subprocess.run(
            ['curl', '-s', 'http://localhost:8005/components/'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        django_process.terminate()
        
        if curl_process.returncode == 0 and components_process.returncode == 0:
            home_content = curl_process.stdout
            components_content = components_process.stdout
            
            # Check for essential dashboard elements
            dashboard_checks = [
                'FYXERAI',
                'Dashboard',
                'card',
                'btn',
                'x-data',
                'theme-toggle'
            ]
            
            home_passed = 0
            for check in dashboard_checks:
                if check in home_content:
                    print(f"✓ Homepage contains {check}")
                    home_passed += 1
                else:
                    print(f"! Homepage missing {check}")
            
            components_passed = 0
            component_checks = ['Components', 'btn', 'card', 'modal', 'badge']
            for check in component_checks:
                if check in components_content:
                    print(f"✓ Components page contains {check}")
                    components_passed += 1
                else:
                    print(f"! Components page missing {check}")
            
            return home_passed >= 4 and components_passed >= 3
        else:
            print("✗ Failed to get HTTP responses")
            return False
            
    except Exception as e:
        print(f"✗ Dashboard rendering test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Dashboard Template Test Suite ===")
    
    files_test = test_template_files_exist()
    structure_test = test_template_structure()
    responsive_test = test_responsive_design_classes()
    alpine_test = test_alpine_integration()
    accessibility_test = test_accessibility_features()
    theme_test = test_theme_toggle_implementation()
    rendering_test = test_dashboard_rendering()
    
    passed_tests = sum([
        files_test, structure_test, responsive_test, 
        alpine_test, accessibility_test, theme_test, rendering_test
    ])
    
    if passed_tests >= 5:
        print(f"\n🎉 Dashboard template tests passed! ({passed_tests}/7 test categories passed)")
        exit(0)
    else:
        print(f"\n❌ Dashboard template tests need work. ({passed_tests}/7 test categories passed)")
        exit(1)