#!/usr/bin/env python
"""Quick script to check test coverage."""

import subprocess
import sys

# Run tests with coverage
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 
     'tests/integration/', 'tests/unit/', 
     '--cov=src/worldenergydata', 
     '--cov-report=term', 
     '--tb=no', '-q'],
    capture_output=True,
    text=True,
    cwd='C:/Users/Sk Samdan/Desktop/github/worldenergydata'
)

# Extract and print coverage percentage
lines = result.stdout.split('\n')
for line in lines:
    if 'TOTAL' in line:
        parts = line.split()
        if len(parts) >= 5:
            print(f"Total Coverage: {parts[-1]}")
            break
else:
    # If TOTAL not found, print last few lines
    print("Coverage report (last 10 lines):")
    for line in lines[-10:]:
        if line.strip():
            print(line)