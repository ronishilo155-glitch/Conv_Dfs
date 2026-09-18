import numpy as np
import os


def load_hex_file(path):
    vals = []

    with open(path, 'r') as f:
        for line in f:
            # Remove comments
            line = line.split('#')[0].strip()

            if not line:
                continue

            for x in line.split():
                vals.append(int(x, 16))

    return np.array(vals, dtype=np.int32)


def bytes_to_int32_le(byte_list, start_idx):
    return (
        int(byte_list[start_idx])
        | (int(byte_list[start_idx + 1]) << 8)
        | (int(byte_list[start_idx + 2]) << 16)
        | (int(byte_list[start_idx + 3]) << 24)
    )


def load_config(path):
    vals = load_hex_file(path)

    input_height = bytes_to_int32_le(vals, 24)
    input_width  = bytes_to_int32_le(vals, 28)
    kernel_size  = bytes_to_int32_le(vals, 32)
    stride       = bytes_to_int32_le(vals, 36)

    return input_height, input_width, kernel_size, stride


def conv_recursive(matrix, kernel, stride):
    if matrix.shape == (16, 16):
        return matrix

    kh, kw = kernel.shape
    out_h = ((matrix.shape[0] - kh) // stride) + 1
    out_w = ((matrix.shape[1] - kw) // stride) + 1

    out = np.zeros((out_h, out_w), dtype=np.int32)

    for i in range(out_h):
        for j in range(out_w):
            r = i * stride
            c = j * stride

            window = matrix[r:r + kh, c:c + kw]

            val = np.sum(window * kernel)
            val = max(0, val)   # ReLU
            val = val >> 2      # Scaling like C

            out[i, j] = val

    return conv_recursive(out, kernel, stride)


def main():
    base_dir = "t0"

    input_path = os.path.join(base_dir, "conv_input.txt")
    kernel_path = os.path.join(base_dir, "conv_kernels.txt")
    config_path = os.path.join(base_dir, "conv_config.txt")
    output_path = os.path.join(base_dir, "conv_expected.txt")

    input_height, input_width, kernel_size, stride = load_config(config_path)

    input_data = load_hex_file(input_path)
    kernel_data = load_hex_file(kernel_path)

    input_matrix = input_data.reshape((input_height, input_width))
    kernel = kernel_data[:kernel_size * kernel_size].reshape((kernel_size, kernel_size))

    final_matrix = conv_recursive(input_matrix, kernel, stride)

    flat_vector = final_matrix.flatten().astype(np.uint8)

    with open(output_path, "w") as f:
        f.write("# Flat Vector Output (256 values)\n")
        for i in range(0, len(flat_vector), 32):
            f.write(" ".join(f"{x:02x}" for x in flat_vector[i:i + 32]) + "\n")

    print(f"Input dimension: {input_height}x{input_width}")
    print(f"Kernel dimension: {kernel_size}x{kernel_size}")
    print(f"Stride: {stride}")
    print(f"Final output dimension: {final_matrix.shape[0]}x{final_matrix.shape[1]}")
    print(f"Saved to: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()