"""
Test file to verify Tailwind CSS installation and compilation.
"""
import os
import subprocess
from pathlib import Path

def test_tailwind_css_compilation():
    """Test that Tailwind CSS can be compiled successfully."""
    
    # Check if required files exist
    project_root = Path(__file__).parent.parent
    
    # Files that should exist after setup
    required_files = [
        project_root / 'package.json',
        project_root / 'tailwind.config.cjs',
        project_root / 'postcss.config.cjs',
        project_root / 'static' / 'css' / 'input.css',
    ]
    
    print("Testing Tailwind CSS setup requirements...")
    
    for file_path in required_files:
        if file_path.exists():
            print(f"✓ {file_path.name} exists")
        else:
            print(f"✗ {file_path.name} missing")
            return False
    
    # Test CSS compilation
    try:
        result = subprocess.run(
            ['npm', 'run', 'build-css'], 
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ CSS compilation successful")
            
            # Check if output file was created
            output_css = project_root / 'static' / 'css' / 'output.css'
            if output_css.exists() and output_css.stat().st_size > 0:
                print("✓ CSS output file created and not empty")
                return True
            else:
                print("✗ CSS output file not created or empty")
                return False
        else:
            print(f"✗ CSS compilation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ CSS compilation timed out")
        return False
    except FileNotFoundError:
        print("✗ npm not found - Node.js dependencies not installed")
        return False

def test_django_static_files():
    """Test that Django can serve static files correctly."""
    
    project_root = Path(__file__).parent.parent
    
    # Check if Django settings are configured for static files
    settings_file = project_root / 'fyxerai_assistant' / 'settings.py'
    
    if not settings_file.exists():
        print("✗ Django settings.py not found")
        return False
    
    settings_content = settings_file.read_text()
    
    # Check for required static file settings
    required_settings = [
        'STATIC_URL',
        'STATICFILES_DIRS'
    ]
    
    print("Testing Django static file configuration...")
    
    for setting in required_settings:
        if setting in settings_content:
            print(f"✓ {setting} configured")
        else:
            print(f"✗ {setting} not configured")
            return False
    
    return True

if __name__ == "__main__":
    print("=== Frontend Setup Test Suite ===")
    
    django_test = test_django_static_files()
    tailwind_test = test_tailwind_css_compilation()
    
    if django_test and tailwind_test:
        print("\n🎉 All frontend setup tests passed!")
        exit(0)
    else:
        print("\n❌ Some tests failed. Check output above.")
        exit(1)