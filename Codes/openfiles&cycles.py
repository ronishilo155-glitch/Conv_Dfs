import numpy as np
import os
import sys
import time

VALID_SIZES = [16, 32, 64, 128, 256]

def run_perf_test(N):
    base_dir = os.getcwd()
    # 1. Validation
    if N not in VALID_SIZES:
        print("Invalid size")
        return

    # 2. Generate grayscale input
    image = np.random.randint(0, 256, (N, N), dtype=np.uint8)

    # 3. Write input files
    # np.savetxt("t0/mnist_input.txt", image.flatten(), fmt="%02x")
    # os.chmod("t0/mnist_input.txt", 0o666)
    # with open("t0/mnist_size.txt", "w") as f:
    #    f.write(str(N))
    #os.chmod("t0/mnist_size.txt", 0o666)
    # 3. Write input files
    # 3. Write input files
    # 3. Write input files
   # 3. Write input files
 # 3. Write input files
    # Using relative path to the pre-existing t0 directory
    # 3. Write input files
    # Get the directory where the script is running
    # 3. Write input files
    # We use the EXACT absolute path from your 'ls' command to avoid any confusion
    # 3. Write input files
    # 3. Write input files
    # We define the directory path
   # 3. Write input files
    # 3. Write input files
    # 3. Write input files
   # 3. Write input files
   # 3. Write input files
    # 3. Write input files
    # 3. Write input files
    # 3. Write input files
    t0_dir = "/project/tsmc65/users/shmilas/ws/my_k5_proj/sim/t0"
    mnist_size_path = os.path.join(t0_dir, "mnist_size.txt")
    mnist_input_path = os.path.join(t0_dir, "mnist_input.txt")

    # Write N
    with open(mnist_size_path, "w") as f:
        f.write(f"{N}\n")

    # Write Pixels: Clean Hex format for fast load
    with open(mnist_input_path, "w") as f:
        for pixel in image.flatten():
            # Crucial: Each hex value followed by a newline
            f.write(f"{int(pixel):02x}\n")
        f.flush()
        os.fsync(f.fileno())

    os.chmod(mnist_size_path, 0o666)
    os.chmod(mnist_input_path, 0o666)
    print(f"PY: Input files (Clean Hex) ready for N={N}")
    # 4. Run C bare-metal application
    # NOTE: In this environment, the C application is run manually
    # in the second terminal (k5_terminal), so we do NOT call os.system here.
    cycles_path = os.path.join(base_dir, "t0", "cycles_result.txt")
    if os.path.exists(cycles_path):
        os.remove(cycles_path)
        print("Wait 2 seconds before starting server...")
    time.sleep(2)
    ret = os.system("python3 /project/tsmc65/shared/k5_share/kuntz5/py/k5_server.py -xbox -mx10 my_conv")
    if ret != 0:
        print("C application failed")
        return
    
    result_path = "t0/cycles_result.txt"
    while not os.path.exists(result_path):
        time.sleep(1)
    time.sleep(0.5)
     
    
    # 5. Read cycles
    #if not os.path.exists("cycles_result.txt"):
    #    print("cycles_result.txt not found")
    #    return

    #with open("cycles_result.txt", "r") as f:
    #    cycles = int(f.read().strip())

    #print(f"N={N}, cycles={cycles}")
    

    with open(result_path, "r") as f:
        cycles = int(f.read().strip())

    print(f"N={N}, cycles={cycles}")

    # Optional logging
    with open("performance_report.log", "a") as report:
        report.write(f"N={N}, cycles={cycles}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_perf_test(int(sys.argv[1]))
    else:
        run_perf_test(32)
