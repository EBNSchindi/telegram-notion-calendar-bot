#!/usr/bin/env python3
"""Minimal test runner for specific tests."""
import subprocess
import sys
import os

# Set test environment variables
os.environ['ENVIRONMENT'] = 'testing'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_telegram_token'
os.environ['NOTION_API_KEY'] = 'test_notion_api_key'
os.environ['NOTION_DATABASE_ID'] = 'test_database_id'
os.environ['OPENAI_API_KEY'] = 'test_openai_api_key'
os.environ['SHARED_NOTION_DATABASE_ID'] = 'test_shared_database_id'

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Run tests directly
test_files = [
    "tests/test_appointment_model.py",
    "tests/test_ai_assistant_service.py",
    "tests/test_appointment_integration.py"
]

# Run tests without conftest
cmd = [sys.executable, "-m", "pytest"] + test_files + [
    "-v", 
    "--tb=short",
    "--no-cov",  # Disable coverage for now
    "--confcutdir=/tmp"  # Prevent loading conftest.py
]

print(f"Running command: {' '.join(cmd)}")
result = subprocess.run(cmd)
sys.exit(result.returncode)