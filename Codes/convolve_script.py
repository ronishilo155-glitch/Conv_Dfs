import numpy as np
import os

def run_my_custom_conv_32_to_flat_256():
    # --- Path Definitions ---
    base_dir = "t0"
    input_path = os.path.join(base_dir, "conv_input.txt")
    output_path = os.path.join(base_dir, "conv_expected.txt")

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found!")
        return

    # 1. Load Input (Expected 1024 bytes for 32x32)
    with open(input_path, 'r') as f:
        hex_vals = [val for line in f if not line.startswith('#') for val in line.split()]
    
    input_data = np.array([int(h, 16) for h in hex_vals], dtype=np.uint8)
    
    # Check if input size matches 32x32 requirements
    if len(input_data) < 1024:
        print(f"Warning: Input size is {len(input_data)}, padding with zeros to 1024")
        input_data = np.pad(input_data, (0, 1024 - len(input_data)))
        
    input_matrix = input_data[:1024].reshape((32, 32))

    # 2. Define 2x2 Kernel and Stride 2
    # Kernel of ones effectively sums the window
    kernel = np.ones((2, 2), dtype=np.int32)
    stride = 2

    # 3. Convolution Calculation
    output_list = []
    
    # Loop 16 times for rows and 16 times for columns = 256 outputs
    for i in range(16):
        for j in range(16):
            row = i * stride
            col = j * stride
            
            # Extract 2x2 Window
            window = input_matrix[row:row+2, col:col+2]
            
            # Calculate Sum (Multiplying by kernel of ones)
            res = np.sum(window)
            
            # ReLU and Shift 2 (Division by 4)
            res = max(0, res) >> 2
            
            # Clip to Byte range (0-255)
            output_list.append(min(res, 255))

    # 4. Convert to Flat Vector
    flat_vector = np.array(output_list, dtype=np.uint8)

    # 5. Save as a vector of 256 values
    output_hex = [f"{v:02x}" for v in flat_vector]
    
    with open(output_path, "w") as f:
        f.write("# Flat Vector Output (256 values)\n")
        # Write values in blocks of 32 for readability
        for i in range(0, len(output_hex), 32):
            f.write(" ".join(output_hex[i:i+32]) + "\n")

    print(f"Success! Generated a flat vector of {len(flat_vector)} values.")
    print(f"Saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    run_my_custom_conv_32_to_flat_256()