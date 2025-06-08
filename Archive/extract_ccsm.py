import subprocess
import os
import json
from pathlib import Path
import shutil

def extract_nsis_installer(exe_path, output_dir=None):
    """Extract contents of NSIS installer using 7z."""
    exe_path = Path(exe_path)
    if output_dir is None:
        output_dir = exe_path.parent / f"{exe_path.stem}_extracted"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Check if 7z is installed
    try:
        subprocess.run(['7z', '--help'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("7z not found. Installing via Homebrew...")
        subprocess.run(['brew', 'install', 'p7zip'], check=True)
    
    # Extract the installer
    print(f"Extracting {exe_path} to {output_dir}...")
    try:
        # First try to list contents
        list_cmd = ['7z', 'l', str(exe_path)]
        list_result = subprocess.run(list_cmd, capture_output=True, text=True, check=True)
        
        # Save the file list
        with open(output_dir / 'file_list.txt', 'w') as f:
            f.write(list_result.stdout)
        
        # Now extract
        extract_cmd = ['7z', 'x', str(exe_path), f'-o{output_dir}']
        subprocess.run(extract_cmd, check=True)
        
        # Analyze extracted contents
        contents = {
            'extracted_files': [],
            'executables': [],
            'dlls': [],
            'data_files': [],
            'other_files': []
        }
        
        for root, _, files in os.walk(output_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(output_dir)
                file_info = {
                    'path': str(rel_path),
                    'size': full_path.stat().st_size,
                    'type': 'other'
                }
                
                # Categorize files
                if file.endswith('.exe'):
                    file_info['type'] = 'executable'
                    contents['executables'].append(file_info)
                elif file.endswith('.dll'):
                    file_info['type'] = 'dll'
                    contents['dlls'].append(file_info)
                elif file.endswith(('.dat', '.txt', '.ini', '.cfg', '.json')):
                    file_info['type'] = 'data'
                    contents['data_files'].append(file_info)
                else:
                    contents['other_files'].append(file_info)
                
                contents['extracted_files'].append(file_info)
        
        # Save analysis
        with open(output_dir / 'extraction_analysis.json', 'w') as f:
            json.dump(contents, f, indent=2)
        
        print(f"\nExtraction complete! Contents saved to {output_dir}")
        print("\nQuick summary:")
        print(f"Total files extracted: {len(contents['extracted_files'])}")
        print(f"Executables: {len(contents['executables'])}")
        print(f"DLLs: {len(contents['dlls'])}")
        print(f"Data files: {len(contents['data_files'])}")
        print(f"Other files: {len(contents['other_files'])}")
        
        return contents
        
    except subprocess.CalledProcessError as e:
        print(f"Error during extraction: {e}")
        print("Command output:", e.output.decode() if e.output else "No output")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract_ccsm.py <path_to_installer.exe> [output_directory]")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    extract_nsis_installer(exe_path, output_dir) 