#!/usr/bin/env python3
"""
Test suite for environment setup validation.
Tests virtual environment creation and Python version requirements.
"""

import os
import sys
import subprocess
import unittest
from pathlib import Path


class TestEnvironmentSetup(unittest.TestCase):
    """Test environment setup requirements for FYXERAI-GEDS."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.venv_path = self.project_root / ".venv"

    def test_python_version_compatibility(self):
        """Test that Python version is compatible (3.11+)."""
        version_info = sys.version_info
        self.assertGreaterEqual(
            version_info.major, 3, "Python major version must be 3 or higher"
        )
        self.assertGreaterEqual(
            version_info.minor,
            11,
            f"Python minor version must be 11 or higher, found {version_info.minor}",
        )

    def test_python_executable_available(self):
        """Test that Python executable is available in PATH."""
        result = subprocess.run(
            ["python3", "--version"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "python3 executable not found in PATH")
        self.assertIn("Python 3.", result.stdout, "Invalid Python version output")

    def test_virtual_environment_creation(self):
        """Test that virtual environment can be created."""
        # Clean up any existing venv for clean test
        if self.venv_path.exists():
            import shutil

            shutil.rmtree(self.venv_path)

        # Create virtual environment
        result = subprocess.run(
            ["python3", "-m", "venv", str(self.venv_path)],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        self.assertEqual(
            result.returncode,
            0,
            f"Virtual environment creation failed: {result.stderr}",
        )
        self.assertTrue(
            self.venv_path.exists(), "Virtual environment directory not created"
        )

        # Test virtual environment structure
        self.assertTrue(
            (self.venv_path / "bin").exists(),
            "Virtual environment bin directory missing",
        )
        self.assertTrue(
            (self.venv_path / "lib").exists(),
            "Virtual environment lib directory missing",
        )
        self.assertTrue(
            (self.venv_path / "pyvenv.cfg").exists(),
            "Virtual environment config missing",
        )

    def test_virtual_environment_activation(self):
        """Test that virtual environment can be activated."""
        if not self.venv_path.exists():
            self.skipTest("Virtual environment not created yet")

        # Test activation by checking Python executable path
        venv_python = self.venv_path / "bin" / "python"
        self.assertTrue(
            venv_python.exists(), "Virtual environment Python executable not found"
        )

        # Test that venv Python returns correct path
        result = subprocess.run(
            [str(venv_python), "-c", "import sys; print(sys.executable)"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode, 0, "Virtual environment Python execution failed"
        )
        self.assertIn(
            str(self.venv_path),
            result.stdout,
            "Virtual environment not properly isolated",
        )

    def test_pip_available_in_venv(self):
        """Test that pip is available in virtual environment."""
        if not self.venv_path.exists():
            self.skipTest("Virtual environment not created yet")

        venv_pip = self.venv_path / "bin" / "pip"
        self.assertTrue(venv_pip.exists(), "pip not found in virtual environment")

        # Test pip functionality
        result = subprocess.run(
            [str(venv_pip), "--version"], capture_output=True, text=True
        )

        self.assertEqual(
            result.returncode, 0, "pip not functional in virtual environment"
        )
        self.assertIn("pip", result.stdout.lower(), "Invalid pip version output")

    def test_project_structure_requirements(self):
        """Test that project root has required structure."""
        self.assertTrue(self.project_root.exists(), "Project root directory not found")
        self.assertTrue(self.project_root.is_dir(), "Project root is not a directory")

        # Test that we can write to project root (for Django project creation)
        test_file = self.project_root / "test_write_permissions.tmp"
        try:
            test_file.write_text("test")
            self.assertTrue(test_file.exists(), "Cannot write to project root")
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_required_directories_can_be_created(self):
        """Test that required directories can be created for Django project."""
        test_dirs = ["static", "media", "logs"]

        created = []
        for dir_name in test_dirs:
            test_dir = self.project_root / dir_name
            if not test_dir.exists():
                test_dir.mkdir(parents=True, exist_ok=True)
                created.append(test_dir)
            self.assertTrue(
                test_dir.exists(), f"Could not create directory: {dir_name}"
            )
            self.assertTrue(test_dir.is_dir(), f"{dir_name} is not a directory")

        # Cleanup only directories we created and are empty
        for d in created:
            try:
                d.rmdir()
            except OSError:
                # Non-empty, leave it
                pass


class TestSystemRequirements(unittest.TestCase):
    """Test system-level requirements for development."""

    def test_git_available(self):
        """Test that Git is available for version control."""
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "Git not available in PATH")
        self.assertIn("git version", result.stdout, "Invalid Git version output")

    def test_required_python_modules(self):
        """Test that required Python modules can be imported."""
        required_modules = ["venv", "sqlite3", "json", "urllib"]

        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                self.fail(f"Required Python module '{module_name}' not available")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
