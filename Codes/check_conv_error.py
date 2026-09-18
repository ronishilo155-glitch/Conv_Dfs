import numpy as np
import os

def check_and_average_errors():
    # Paths (Assumes running from 'sim' folder)
    expected_path = os.path.join("t0", "conv_expected.txt")
    actual_path = os.path.join("t0", "conv_output.txt")
    log_file_path = "all_errors.log" 

    def load_hex(path):
        if not os.path.exists(path): 
            return None
        with open(path, 'r') as f:
            # Loading hex values, ignoring lines starting with '#'
            vals = [int(h, 16) for line in f if not line.startswith('#') for h in line.split()]
        return np.array(vals[:256], dtype=np.int32)

    # 1. Load Data
    expected = load_hex(expected_path)
    actual = load_hex(actual_path)

    if expected is None or actual is None:
        print(f"Error: Missing files in {os.path.abspath('t0')}")
        return

    # 2. Calculate Error (MSE)
    diff = actual - expected
    current_mse = np.mean(diff**2)
    
    # 3. Save current run error to the log file (Append mode)
    with open(log_file_path, "a") as log_f:
        log_f.write(f"Run Error: {current_mse:.4f}\n")

    # 4. Read history from log to calculate current average
    with open(log_file_path, "r") as log_f:
        lines = log_f.readlines()
        # Extract only numeric values from lines starting with "Run Error"
        errors_list = []
        for line in lines:
            if "Run Error:" in line:
                try:
                    errors_list.append(float(line.split(":")[1].strip()))
                except ValueError:
                    continue

    num_runs = len(errors_list)
    current_avg = sum(errors_list) / num_runs

    print(f"\n--- Run #{num_runs} Statistics ---")
    print(f"Log File Path: {os.path.abspath(log_file_path)}")
    print(f"Current Run MSE: {current_mse:.4f}")

    # 5. Handle completion of 4 runs
    if num_runs == 4:
        with open(log_file_path, "a") as log_f:
            log_f.write("-" * 35 + "\n")
            log_f.write(f"FINAL AVERAGE OF 4 RUNS: {current_avg:.4f}\n")
            log_f.write("-" * 35 + "\n")
        
        print("\n" + "="*45)
        print(f"DONE: Reached 4 runs!")
        print(f"FINAL AVERAGE: {current_avg:.4f}")
        print(f"Summary saved to {log_file_path}")
        print("="*45)
    else:
        print(f"Current Average ({num_runs} runs): {current_avg:.4f}")
        print(f"Need {4 - num_runs} more runs to complete the set.")

if __name__ == "__main__":
    check_and_average_errors()