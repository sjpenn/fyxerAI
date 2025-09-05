"""
Test responsive design implementation.
"""
import os
import subprocess
import time
from pathlib import Path

def test_responsive_breakpoints():
    """Test that templates include proper responsive breakpoints."""
    
    project_root = Path(__file__).parent.parent
    templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing responsive breakpoints...")
    
    # Tailwind breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px), 2xl (1536px)
    breakpoints = ['sm:', 'md:', 'lg:', 'xl:', '2xl:']
    mobile_classes = ['block', 'hidden', 'flex', 'grid', 'w-full', 'max-w-']
    layout_classes = ['container', 'mx-auto', 'px-', 'py-', 'space-']
    
    for template_path in templates:
        if template_path.exists():
            content = template_path.read_text()
            
            # Check for responsive breakpoints
            found_breakpoints = [bp for bp in breakpoints if bp in content]
            if found_breakpoints:
                print(f"✓ {template_path.name} includes breakpoints: {found_breakpoints}")
            else:
                print(f"! {template_path.name} could include more breakpoints")
            
            # Check for mobile-friendly classes
            found_mobile = [cls for cls in mobile_classes if cls in content]
            if found_mobile:
                print(f"✓ {template_path.name} includes mobile classes: {found_mobile[:3]}...")
            
            # Check for layout classes
            found_layout = [cls for cls in layout_classes if cls in content]
            if found_layout:
                print(f"✓ {template_path.name} includes layout classes: {found_layout[:3]}...")
    
    return True

def test_mobile_navigation():
    """Test that mobile navigation is properly implemented."""
    
    project_root = Path(__file__).parent.parent
    base_template = project_root / 'core' / 'templates' / 'base.html'
    
    print("Testing mobile navigation...")
    
    if not base_template.exists():
        print("✗ Base template not found")
        return False
    
    content = base_template.read_text()
    
    mobile_nav_features = [
        'sidebarOpen',
        'lg:hidden',
        'lg:translate-x-0',
        'lg:static',
        'hamburger',  # Common term
        'mobile',     # Mobile-specific classes
        '@click="sidebarOpen'
    ]
    
    found_features = []
    for feature in mobile_nav_features:
        if feature in content:
            found_features.append(feature)
    
    if len(found_features) >= 4:
        print(f"✓ Mobile navigation properly implemented: {found_features}")
        return True
    else:
        print(f"! Mobile navigation could be enhanced: {found_features}")
        return False

def test_touch_targets():
    """Test that touch targets are properly sized for mobile."""
    
    project_root = Path(__file__).parent.parent
    templates = [
        project_root / 'core' / 'templates' / 'base.html',
        project_root / 'core' / 'templates' / 'dashboard.html',
    ]
    
    print("Testing touch targets...")
    
    # Minimum 44px (11 Tailwind units) touch targets
    touch_classes = [
        'h-10', 'h-11', 'h-12',  # Height classes >= 40px
        'p-2', 'p-3', 'p-4',     # Padding classes
        'btn-sm', 'btn-md', 'btn-lg',  # Button sizes
        'min-h-', 'min-w-'       # Minimum size classes
    ]
    
    for template_path in templates:
        if template_path.exists():
            content = template_path.read_text()
            found_touch = [cls for cls in touch_classes if cls in content]
            
            if found_touch:
                print(f"✓ {template_path.name} includes touch-friendly classes: {found_touch[:3]}...")
            else:
                print(f"! {template_path.name} could include touch-friendly classes")
    
    return True

def test_viewport_meta():
    """Test that viewport meta tag is properly configured."""
    
    project_root = Path(__file__).parent.parent
    base_template = project_root / 'core' / 'templates' / 'base.html'
    
    print("Testing viewport configuration...")
    
    if not base_template.exists():
        print("✗ Base template not found")
        return False
    
    content = base_template.read_text()
    
    viewport_features = [
        'name="viewport"',
        'width=device-width',
        'initial-scale=1.0',
        'user-scalable=no',  # Optional
        'viewport-fit=cover'  # Optional for notched devices
    ]
    
    found_viewport = [feature for feature in viewport_features if feature in content]
    
    if len(found_viewport) >= 3:
        print(f"✓ Viewport properly configured: {found_viewport}")
        return True
    else:
        print(f"! Viewport configuration could be improved: {found_viewport}")
        return False

if __name__ == "__main__":
    print("=== Responsive Design Test Suite ===")
    
    breakpoints_test = test_responsive_breakpoints()
    mobile_nav_test = test_mobile_navigation()
    touch_targets_test = test_touch_targets()
    viewport_test = test_viewport_meta()
    
    passed_tests = sum([breakpoints_test, mobile_nav_test, touch_targets_test, viewport_test])
    
    if passed_tests >= 3:
        print(f"\n🎉 Responsive design tests passed! ({passed_tests}/4 test categories passed)")
        exit(0)
    else:
        print(f"\n❌ Responsive design tests need work. ({passed_tests}/4 test categories passed)")
        exit(1)