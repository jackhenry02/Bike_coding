import pefile
import os
import subprocess
import json
from pathlib import Path

def analyze_ccsm_executable(exe_path):
    """Analyze CCSM executable to determine inputs/outputs and dependencies."""
    results = {
        'file_info': {},
        'dependencies': [],
        'io_analysis': {},
        'wine_test': {}
    }
    
    # Basic file info
    exe_path = Path(exe_path)
    results['file_info'] = {
        'name': exe_path.name,
        'size': os.path.getsize(exe_path),
        'modified': os.path.getmtime(exe_path)
    }
    
    try:
        # Try to analyze PE file
        pe = pefile.PE(exe_path)
        results['file_info']['architecture'] = pe.OPTIONAL_HEADER.Magic
        results['file_info']['subsystem'] = pe.OPTIONAL_HEADER.Subsystem
        
        # Get dependencies
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            results['dependencies'].append(entry.dll.decode())
            
    except Exception as e:
        results['file_info']['error'] = f"PE analysis failed: {str(e)}"
    
    # Test with Wine
    try:
        # Try to run with --help or /? to see if it accepts command line args
        help_cmd = ['wine', str(exe_path), '--help']
        help_result = subprocess.run(help_cmd, capture_output=True, text=True, timeout=5)
        results['wine_test']['help_output'] = help_result.stdout
        
        # Try to run with /? as alternative
        if not help_result.stdout:
            help_cmd = ['wine', str(exe_path), '/?']
            help_result = subprocess.run(help_cmd, capture_output=True, text=True, timeout=5)
            results['wine_test']['help_output'] = help_result.stdout
            
    except subprocess.TimeoutExpired:
        results['wine_test']['error'] = "Command timed out"
    except Exception as e:
        results['wine_test']['error'] = f"Wine test failed: {str(e)}"
    
    # Save results
    output_file = exe_path.with_suffix('.analysis.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python analyze_ccsm.py <path_to_ccsm.exe>")
        sys.exit(1)
        
    exe_path = sys.argv[1]
    results = analyze_ccsm_executable(exe_path)
    print(f"Analysis complete. Results saved to {Path(exe_path).with_suffix('.analysis.json')}")
    print("\nQuick summary:")
    print(f"File: {results['file_info'].get('name')}")
    print(f"Architecture: {results['file_info'].get('architecture', 'Unknown')}")
    print(f"Dependencies: {', '.join(results['dependencies'][:5])}...")
    if 'help_output' in results['wine_test']:
        print("\nHelp output:")
        print(results['wine_test']['help_output']) 