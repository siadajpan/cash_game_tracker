"""
Test script to verify reset_db.py works correctly.
This runs through the reset process and verifies the schema.
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and report the result."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print(f"❌ Failed with exit code {result.returncode}")
        return False
    else:
        print(f"✓ Success")
        return True


def main():
    """Run the test sequence."""
    print("\n" + "="*60)
    print("TESTING DATABASE RESET WORKFLOW")
    print("="*60)
    
    # Determine if we're on Windows or Linux
    is_windows = os.name == 'nt'
    python_cmd = "poetry run python"
    
    tests = [
        (f"{python_cmd} backend/db/tools/reset_db.py reset", 
         "Full database reset (drop + create)"),
        (f"{python_cmd} backend/db/tools/verify_schema.py", 
         "Schema verification"),
    ]
    
    all_passed = True
    for cmd, desc in tests:
        # Adjust path separators for Windows
        if is_windows:
            cmd = cmd.replace('/', '\\')
        
        if not run_command(cmd, desc):
            all_passed = False
            print("\n❌ Test failed. Stopping.")
            break
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
