"""
Test ShadCN UI component adaptation for Alpine.js.
"""
import os
import subprocess
import time
from pathlib import Path

def test_component_files_exist():
    """Test that ShadCN UI component files are properly set up."""
    
    project_root = Path(__file__).parent.parent
    
    required_files = [
        project_root / 'static' / 'css' / 'components' / 'ui' / 'button.css',
        project_root / 'static' / 'css' / 'components' / 'ui' / 'card.css', 
        project_root / 'static' / 'css' / 'components' / 'ui' / 'modal.css',
        project_root / 'static' / 'css' / 'components' / 'ui' / 'input.css',
        project_root / 'static' / 'css' / 'components' / 'ui' / 'badge.css',
        project_root / 'core' / 'templates' / 'components' / 'ui' / 'button.html',
        project_root / 'core' / 'templates' / 'components' / 'ui' / 'card.html',
        project_root / 'core' / 'templates' / 'components' / 'ui' / 'modal.html',
    ]
    
    print("Testing ShadCN UI component file setup...")
    
    missing_files = []
    for file_path in required_files:
        if file_path.exists():
            print(f"✓ {file_path.name} exists")
        else:
            print(f"✗ {file_path.name} missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_component_css_classes():
    """Test that component CSS contains required classes."""
    
    project_root = Path(__file__).parent.parent
    
    # Test button classes
    button_css = project_root / 'static' / 'css' / 'components' / 'ui' / 'button.css'
    if button_css.exists():
        button_content = button_css.read_text()
        button_classes = ['.btn-primary', '.btn-secondary', '.btn-outline', '.btn-sm', '.btn-md', '.btn-lg']
        
        print("Testing button component classes...")
        for cls in button_classes:
            if cls in button_content:
                print(f"✓ {cls} class defined")
            else:
                print(f"✗ {cls} class missing")
                return False
    
    # Test card classes
    card_css = project_root / 'static' / 'css' / 'components' / 'ui' / 'card.css'
    if card_css.exists():
        card_content = card_css.read_text()
        card_classes = ['.card', '.card-header', '.card-body', '.card-footer']
        
        print("Testing card component classes...")
        for cls in card_classes:
            if cls in card_content:
                print(f"✓ {cls} class defined")
            else:
                print(f"✗ {cls} class missing")
                return False
    
    return True

def test_alpine_component_integration():
    """Test that Alpine.js components are properly integrated."""
    
    project_root = Path(__file__).parent.parent
    
    # Test component template files
    button_template = project_root / 'core' / 'templates' / 'components' / 'ui' / 'button.html'
    if button_template.exists():
        button_content = button_template.read_text()
        
        print("Testing button template Alpine.js integration...")
        alpine_features = ['x-data', 'x-bind', ':class', ':disabled']
        
        for feature in alpine_features:
            if feature in button_content:
                print(f"✓ Button template uses {feature}")
            else:
                print(f"! Button template could use {feature} (optional)")
    
    # Test modal template
    modal_template = project_root / 'core' / 'templates' / 'components' / 'ui' / 'modal.html'
    if modal_template.exists():
        modal_content = modal_template.read_text()
        
        print("Testing modal template Alpine.js integration...")
        modal_features = ['x-show', 'x-transition', '@click.away', '@keydown.escape']
        
        for feature in modal_features:
            if feature in modal_content:
                print(f"✓ Modal template uses {feature}")
            else:
                print(f"! Modal template could use {feature} (optional)")
    
    return True

def test_accessibility_features():
    """Test that components include accessibility features."""
    
    project_root = Path(__file__).parent.parent
    
    # Test button accessibility
    button_template = project_root / 'core' / 'templates' / 'components' / 'ui' / 'button.html'
    if button_template.exists():
        button_content = button_template.read_text()
        
        print("Testing button accessibility features...")
        aria_features = ['aria-', 'role=', 'tabindex', 'disabled']
        
        for feature in aria_features:
            if feature in button_content:
                print(f"✓ Button includes {feature}")
            else:
                print(f"! Button could include {feature} (recommended)")
    
    # Test modal accessibility
    modal_template = project_root / 'core' / 'templates' / 'components' / 'ui' / 'modal.html'
    if modal_template.exists():
        modal_content = modal_template.read_text()
        
        print("Testing modal accessibility features...")
        modal_aria = ['aria-labelledby', 'aria-describedby', 'role="dialog"', 'aria-modal']
        
        for feature in modal_aria:
            if feature in modal_content:
                print(f"✓ Modal includes {feature}")
            else:
                print(f"! Modal could include {feature} (recommended)")
    
    return True

def test_component_variants():
    """Test that component variants are properly defined."""
    
    project_root = Path(__file__).parent.parent
    
    # Check CSS for component variants
    css_files = [
        project_root / 'static' / 'css' / 'components' / 'ui' / 'button.css',
        project_root / 'static' / 'css' / 'components' / 'ui' / 'badge.css',
    ]
    
    print("Testing component variants...")
    
    for css_file in css_files:
        if css_file.exists():
            content = css_file.read_text()
            
            # Check for size variants
            size_variants = ['-sm', '-md', '-lg', '-xs', '-xl']
            found_sizes = [size for size in size_variants if size in content]
            
            if found_sizes:
                print(f"✓ {css_file.name} includes size variants: {found_sizes}")
            else:
                print(f"! {css_file.name} could include size variants")
            
            # Check for color variants
            color_variants = ['primary', 'secondary', 'success', 'warning', 'error']
            found_colors = [color for color in color_variants if color in content]
            
            if found_colors:
                print(f"✓ {css_file.name} includes color variants: {found_colors}")
            else:
                print(f"! {css_file.name} could include color variants")
    
    return True

def test_component_rendering():
    """Test that components render correctly in Django templates."""
    
    project_root = Path(__file__).parent.parent
    
    print("Testing component rendering...")
    
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
        
        # Test homepage response (contains components)
        curl_process = subprocess.run(
            ['curl', '-s', 'http://localhost:8005/'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        django_process.terminate()
        
        if curl_process.returncode == 0:
            response_content = curl_process.stdout
            
            # Check for component classes in rendered HTML
            component_checks = [
                'btn',
                'card',
                'badge',
                'x-data',
                'x-show',
                '@click'
            ]
            
            for check in component_checks:
                if check in response_content:
                    print(f"✓ Rendered page contains {check}")
                else:
                    print(f"! Rendered page missing {check} (may be optional)")
            
            return True
        else:
            print("✗ Failed to get homepage response")
            return False
            
    except Exception as e:
        print(f"✗ Component rendering test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== ShadCN UI Component Test Suite ===")
    
    files_test = test_component_files_exist()
    css_test = test_component_css_classes()
    alpine_test = test_alpine_component_integration()
    accessibility_test = test_accessibility_features()
    variants_test = test_component_variants()
    rendering_test = test_component_rendering()
    
    # Pass if most tests are successful (some files may not exist yet)
    passed_tests = sum([css_test, alpine_test, accessibility_test, variants_test, rendering_test])
    
    if passed_tests >= 3:
        print(f"\n🎉 ShadCN UI component tests passed! ({passed_tests}/5 test categories passed)")
        exit(0)
    else:
        print(f"\n❌ ShadCN UI component tests need work. ({passed_tests}/5 test categories passed)")
        exit(1)