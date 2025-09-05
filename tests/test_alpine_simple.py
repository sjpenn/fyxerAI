"""
Simple Alpine.js component verification without browser automation.
"""
import os
import subprocess
import time
from pathlib import Path

def test_alpine_files_exist():
    """Test that Alpine.js files are properly set up."""
    
    project_root = Path(__file__).parent.parent
    
    required_files = [
        project_root / 'static' / 'js' / 'alpine.min.js',
        project_root / 'static' / 'js' / 'alpine-config.js',
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing Alpine.js file setup...")
    
    for file_path in required_files:
        if file_path.exists():
            print(f"✓ {file_path.name} exists")
        else:
            print(f"✗ {file_path.name} missing")
            return False
    
    return True

def test_alpine_config_content():
    """Test that Alpine.js configuration contains required stores and components."""
    
    project_root = Path(__file__).parent.parent
    config_file = project_root / 'static' / 'js' / 'alpine-config.js'
    
    if not config_file.exists():
        print("✗ Alpine config file not found")
        return False
    
    config_content = config_file.read_text()
    
    # Check for required stores
    required_stores = ['theme', 'preferences', 'app']
    required_components = ['themeToggle', 'modal', 'dropdown', 'toast']
    
    print("Testing Alpine.js configuration content...")
    
    for store in required_stores:
        if f"Alpine.store('{store}'" in config_content:
            print(f"✓ {store} store configured")
        else:
            print(f"✗ {store} store not configured")
            return False
    
    for component in required_components:
        if f"{component}()" in config_content:
            print(f"✓ {component} component pattern defined")
        else:
            print(f"✗ {component} component pattern not defined")
            return False
    
    return True

def test_template_alpine_integration():
    """Test that templates properly integrate Alpine.js."""
    
    project_root = Path(__file__).parent.parent
    base_template = project_root / 'core' / 'templates' / 'base.html'
    dashboard_template = project_root / 'core' / 'templates' / 'dashboard.html'
    
    print("Testing template Alpine.js integration...")
    
    if not base_template.exists():
        print("✗ Base template not found")
        return False
    
    base_content = base_template.read_text()
    
    # Check for Alpine.js integration in base template
    alpine_checks = [
        'alpine.min.js',
        'alpine-config.js',
        'x-data',
        '$store.theme',
        'data-theme-toggle'
    ]
    
    for check in alpine_checks:
        if check in base_content:
            print(f"✓ Base template contains {check}")
        else:
            print(f"✗ Base template missing {check}")
            return False
    
    # Check dashboard template for Alpine components
    if dashboard_template.exists():
        dashboard_content = dashboard_template.read_text()
        
        dashboard_checks = [
            'x-data',
            'x-show',
            'x-transition',
            '@click'
        ]
        
        for check in dashboard_checks:
            if check in dashboard_content:
                print(f"✓ Dashboard template contains {check}")
            else:
                print(f"✗ Dashboard template missing {check}")
                return False
    
    return True

def test_django_server_response():
    """Test that Django server responds successfully."""
    
    project_root = Path(__file__).parent.parent
    
    print("Testing Django server response...")
    
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
        
        # Test server response
        curl_process = subprocess.run(
            ['curl', '-s', '-I', 'http://localhost:8005/'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        django_process.terminate()
        
        if curl_process.returncode == 0 and '200 OK' in curl_process.stdout:
            print("✓ Django server responds successfully")
            return True
        else:
            print("✗ Django server not responding correctly")
            return False
            
    except Exception as e:
        print(f"✗ Server test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Alpine.js Simple Test Suite ===")
    
    files_test = test_alpine_files_exist()
    config_test = test_alpine_config_content()
    template_test = test_template_alpine_integration()
    server_test = test_django_server_response()
    
    if files_test and config_test and template_test and server_test:
        print("\n🎉 All Alpine.js integration tests passed!")
        exit(0)
    else:
        print("\n❌ Some Alpine.js tests failed. Check output above.")
        exit(1)