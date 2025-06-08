import subprocess
import os
import sys
from pathlib import Path
import json
import time

class CCSMRunner:
    def __init__(self, exe_path):
        self.exe_path = Path(exe_path)
        self.working_dir = self.exe_path.parent
        self.log_file = self.exe_path.with_suffix('.log')
        
    def run(self, input_file=None, output_file=None, timeout=300):
        """Run CCSM with optional input/output files."""
        cmd = ['wine', str(self.exe_path)]
        
        # Add input file if provided
        if input_file:
            cmd.append(str(input_file))
            
        # Add output file if provided
        if output_file:
            cmd.append(str(output_file))
            
        # Prepare environment
        env = os.environ.copy()
        env['WINEDEBUG'] = '-all'  # Suppress Wine debug output
        
        try:
            # Run the command
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                cwd=self.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Log the command
            with open(self.log_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*50}\n")
            
            # Stream output to both console and log file
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    with open(self.log_file, 'a') as f:
                        f.write(output)
                        
            # Get any remaining output
            stdout, stderr = process.communicate(timeout=timeout)
            
            # Log completion
            end_time = time.time()
            with open(self.log_file, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {end_time - start_time:.2f} seconds\n")
                f.write(f"Exit code: {process.returncode}\n")
                if stderr:
                    f.write(f"Errors:\n{stderr}\n")
                f.write(f"{'='*50}\n")
            
            return {
                'success': process.returncode == 0,
                'exit_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'duration': end_time - start_time
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            with open(self.log_file, 'a') as f:
                f.write(f"\nProcess timed out after {timeout} seconds\n")
            return {
                'success': False,
                'error': f'Process timed out after {timeout} seconds'
            }
            
        except Exception as e:
            with open(self.log_file, 'a') as f:
                f.write(f"\nError: {str(e)}\n")
            return {
                'success': False,
                'error': str(e)
            }

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_ccsm.py <path_to_ccsm.exe> [input_file] [output_file]")
        sys.exit(1)
        
    exe_path = sys.argv[1]
    input_file = sys.argv[2] if len(sys.argv) > 2 else None
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    runner = CCSMRunner(exe_path)
    result = runner.run(input_file, output_file)
    
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
        
    print(f"\nProcess completed successfully in {result['duration']:.2f} seconds")
    print(f"Log file: {runner.log_file}")

if __name__ == "__main__":
    main()
