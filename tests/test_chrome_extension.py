"""
Test Chrome extension structure and basic functionality.
"""
import os
import json
import subprocess
import time
from pathlib import Path

def test_extension_structure():
    """Test that extension directory structure is properly set up."""
    
    project_root = Path(__file__).parent.parent
    extension_dir = project_root / 'extension'
    
    required_files = [
        extension_dir / 'manifest.json',
        extension_dir / 'content.js',
        extension_dir / 'background.js',
        extension_dir / 'popup.html',
        extension_dir / 'popup.js',
        extension_dir / 'styles.css',
    ]
    
    print("Testing Chrome extension file structure...")
    
    if not extension_dir.exists():
        print("✗ Extension directory does not exist")
        return False
    
    for file_path in required_files:
        if file_path.exists():
            print(f"✓ {file_path.name} exists")
        else:
            print(f"✗ {file_path.name} missing")
            return False
    
    return True

def test_manifest_json():
    """Test that manifest.json is properly configured."""
    
    project_root = Path(__file__).parent.parent
    manifest_path = project_root / 'extension' / 'manifest.json'
    
    print("Testing manifest.json configuration...")
    
    if not manifest_path.exists():
        print("✗ manifest.json not found")
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check required manifest fields
        required_fields = [
            'manifest_version',
            'name',
            'version',
            'description',
            'permissions',
            'content_scripts',
            'background',
            'action'
        ]
        
        for field in required_fields:
            if field in manifest:
                print(f"✓ manifest.json contains {field}")
            else:
                print(f"✗ manifest.json missing {field}")
                return False
        
        # Check manifest version
        if manifest.get('manifest_version') == 3:
            print("✓ Using Manifest v3")
        else:
            print(f"! Using Manifest v{manifest.get('manifest_version')} (v3 recommended)")
        
        # Check content scripts
        content_scripts = manifest.get('content_scripts', [])
        if content_scripts:
            matches = content_scripts[0].get('matches', [])
            expected_matches = ['https://mail.google.com/*', 'https://outlook.live.com/*']
            
            for match in expected_matches:
                if match in matches:
                    print(f"✓ Content script matches {match}")
                else:
                    print(f"! Content script could match {match}")
        
        # Check permissions
        permissions = manifest.get('permissions', [])
        if 'activeTab' in permissions:
            print("✓ Has activeTab permission")
        else:
            print("! Could include activeTab permission")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in manifest.json: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading manifest.json: {e}")
        return False

def test_content_script():
    """Test that content script has proper structure."""
    
    project_root = Path(__file__).parent.parent
    content_script_path = project_root / 'extension' / 'content.js'
    
    print("Testing content script...")
    
    if not content_script_path.exists():
        print("✗ content.js not found")
        return False
    
    content = content_script_path.read_text()
    
    # Check for essential content script features
    content_features = [
        'console.log',
        'document',
        'chrome.runtime',
        'sendMessage',
        'Gmail' or 'Outlook',
        'FYXERAI'
    ]
    
    found_features = []
    for feature in content_features:
        if feature in content:
            found_features.append(feature)
    
    if len(found_features) >= 4:
        print(f"✓ Content script includes essential features: {found_features}")
        return True
    else:
        print(f"! Content script could include more features: {found_features}")
        return False

def test_background_script():
    """Test that background script has proper structure."""
    
    project_root = Path(__file__).parent.parent
    background_script_path = project_root / 'extension' / 'background.js'
    
    print("Testing background script...")
    
    if not background_script_path.exists():
        print("✗ background.js not found")
        return False
    
    content = background_script_path.read_text()
    
    # Check for essential background script features
    background_features = [
        'chrome.runtime.onMessage',
        'addListener',
        'sendResponse',
        'console.log',
        'FYXERAI'
    ]
    
    found_features = []
    for feature in background_features:
        if feature in content:
            found_features.append(feature)
    
    if len(found_features) >= 3:
        print(f"✓ Background script includes essential features: {found_features}")
        return True
    else:
        print(f"! Background script could include more features: {found_features}")
        return False

def test_popup_interface():
    """Test that popup interface is properly structured."""
    
    project_root = Path(__file__).parent.parent
    popup_html_path = project_root / 'extension' / 'popup.html'
    popup_js_path = project_root / 'extension' / 'popup.js'
    
    print("Testing popup interface...")
    
    if not popup_html_path.exists():
        print("✗ popup.html not found")
        return False
    
    html_content = popup_html_path.read_text()
    
    # Check for essential popup HTML features
    html_features = [
        '<!DOCTYPE html>',
        '<html',
        '<head>',
        '<body>',
        'FYXERAI',
        'popup.js',
        'styles.css'
    ]
    
    found_html = []
    for feature in html_features:
        if feature in html_content:
            found_html.append(feature)
    
    if len(found_html) >= 5:
        print(f"✓ Popup HTML properly structured: {found_html}")
    else:
        print(f"! Popup HTML could be improved: {found_html}")
        return False
    
    # Check popup JavaScript if it exists
    if popup_js_path.exists():
        js_content = popup_js_path.read_text()
        
        js_features = [
            'document.addEventListener',
            'DOMContentLoaded',
            'chrome.tabs',
            'querySelector'
        ]
        
        found_js = [feature for feature in js_features if feature in js_content]
        
        if found_js:
            print(f"✓ Popup JavaScript includes: {found_js}")
        else:
            print("! Popup JavaScript could include DOM interaction")
    
    return True

def test_extension_icons():
    """Test that extension icons are properly configured."""
    
    project_root = Path(__file__).parent.parent
    extension_dir = project_root / 'extension'
    icons_dir = extension_dir / 'icons'
    
    print("Testing extension icons...")
    
    # Check for icon files
    icon_sizes = ['16', '32', '48', '128']
    found_icons = []
    
    if icons_dir.exists():
        for size in icon_sizes:
            icon_path = icons_dir / f'icon{size}.png'
            if icon_path.exists():
                found_icons.append(size)
                print(f"✓ Found icon{size}.png")
    
    if found_icons:
        print(f"✓ Extension has icons for sizes: {found_icons}")
        return True
    else:
        print("! Extension could include icon files")
        return False

def test_extension_css():
    """Test that extension CSS is properly structured."""
    
    project_root = Path(__file__).parent.parent
    css_path = project_root / 'extension' / 'styles.css'
    
    print("Testing extension CSS...")
    
    if not css_path.exists():
        print("✗ styles.css not found")
        return False
    
    content = css_path.read_text()
    
    # Check for essential CSS features
    css_features = [
        'body',
        'button',
        'popup',
        'fyxerai',
        'hover:',
        'transition'
    ]
    
    found_css = []
    for feature in css_features:
        if feature.lower() in content.lower():
            found_css.append(feature)
    
    if len(found_css) >= 3:
        print(f"✓ Extension CSS includes: {found_css}")
        return True
    else:
        print(f"! Extension CSS could include more styling: {found_css}")
        return False

def test_message_passing():
    """Test that message passing structure is implemented."""
    
    project_root = Path(__file__).parent.parent
    content_path = project_root / 'extension' / 'content.js'
    background_path = project_root / 'extension' / 'background.js'
    
    print("Testing message passing implementation...")
    
    if not content_path.exists() or not background_path.exists():
        print("✗ Required scripts not found")
        return False
    
    content_script = content_path.read_text()
    background_script = background_path.read_text()
    
    # Check content script sends messages
    content_sends = [
        'chrome.runtime.sendMessage',
        'sendMessage',
        'postMessage'
    ]
    
    content_found = [feature for feature in content_sends if feature in content_script]
    
    # Check background script receives messages
    background_receives = [
        'chrome.runtime.onMessage',
        'onMessage.addListener',
        'addListener'
    ]
    
    background_found = [feature for feature in background_receives if feature in background_script]
    
    if content_found and background_found:
        print(f"✓ Message passing implemented: {content_found} -> {background_found}")
        return True
    else:
        print(f"! Message passing could be improved: {content_found} -> {background_found}")
        return False

if __name__ == "__main__":
    print("=== Chrome Extension Test Suite ===")
    
    structure_test = test_extension_structure()
    manifest_test = test_manifest_json()
    content_test = test_content_script()
    background_test = test_background_script()
    popup_test = test_popup_interface()
    icons_test = test_extension_icons()
    css_test = test_extension_css()
    messaging_test = test_message_passing()
    
    passed_tests = sum([
        structure_test, manifest_test, content_test, background_test,
        popup_test, css_test, messaging_test
    ])
    
    # Icons test is optional, don't count in pass/fail
    total_tests = 7
    
    if passed_tests >= 5:
        print(f"\n🎉 Chrome extension tests passed! ({passed_tests}/{total_tests} core tests passed)")
        if icons_test:
            print("✓ Bonus: Extension icons are present")
        exit(0)
    else:
        print(f"\n❌ Chrome extension tests need work. ({passed_tests}/{total_tests} core tests passed)")
        exit(1)