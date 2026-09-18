#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

// ------------------------------------------------------------
// 1. Compute pipeline depth
// ------------------------------------------------------------
int compute_depth(int N)
{
    int depth = 0;
    while (N > 16) {
        N /= 2;
        depth++;
    }
    return depth;
}

static inline float relu(float x) { return (x > 0.0f) ? x : 0.0f; }

// ------------------------------------------------------------
// NEW: Extract a tile into a FLAT buffer (no malloc)
// tile_flat size must be T*T
// image is flat N*N: image_flat[r*N + c]
// ------------------------------------------------------------
static void extract_tile_flat(
    const float* image_flat,
    int N,
    int start_r,
    int start_c,
    int T,
    float* tile_flat
) {
    for (int r = 0; r < T; r++) {
        for (int c = 0; c < T; c++) {
            tile_flat[r * T + c] = image_flat[(start_r + r) * N + (start_c + c)];
        }
    }
}

// ------------------------------------------------------------
// NEW: One stage of 2x2 conv stride-2 + ReLU (no malloc)
// in:  n*n   (flat)
// out: (n/2)*(n/2) (flat)
// ------------------------------------------------------------
static void conv2x2_stage_flat(
    const float* in,
    int n,
    const float k[2][2],
    float* out
) {
    int out_size = n / 2;

    for (int r = 0; r < out_size; r++) {
        int br = r * 2;
        for (int c = 0; c < out_size; c++) {
            int bc = c * 2;

            float a = in[br * n + bc];
            float b = in[br * n + bc + 1];
            float c1 = in[(br + 1) * n + bc];
            float d = in[(br + 1) * n + bc + 1];

            float acc = a * k[0][0] + b * k[0][1] + c1 * k[1][0] + d * k[1][1];
            out[r * out_size + c] = relu(acc); // Fusion: Conv + Activation
        }
    }
}

// ------------------------------------------------------------
// NEW: Streaming/Fused pipeline for ONE tile (no malloc)
// Uses two fixed buffers and swaps pointers each stage.
// Assumes T <= 16.
// ------------------------------------------------------------
static float pipeline_process_tile_streaming(
    const float* tile_flat,      // size T*T
    int depth,
    int T,
    const float kernel[2][2]     // (for now) same kernel each stage
) {
    // Fixed max buffers (T max is 16 -> 256 elems)
    float bufA[16 * 16];
    float bufB[16 * 16];

    // Copy tile into bufA
    for (int i = 0; i < T * T; i++) bufA[i] = tile_flat[i];

    int cur = T;
    float* in = bufA;
    float* out = bufB;

    for (int stage = 0; stage < depth; stage++) {
        conv2x2_stage_flat(in, cur, kernel, out);
        cur /= 2;

        // swap
        float* tmp = in; in = out; out = tmp;
    }

    // After depth stages, cur == 1, result in in[0]
    return in[0];
}

// ------------------------------------------------------------
// NEW: Full image processing (no malloc)
// input: image_flat N*N
// output: output_flat out_dim*out_dim
// out_dim = N / T
// ------------------------------------------------------------
static void process_full_image_without_fc_flat(
    const float* image_flat,
    int N,
    const float kernel[2][2],
    float* output_flat,
    int* out_dim_result
) {
    int depth = compute_depth(N);
    int T = 1 << depth;
    int out_dim = N / T;
    if (out_dim_result) *out_dim_result = out_dim;

    for (int tr = 0; tr < out_dim; tr++) {
        for (int tc = 0; tc < out_dim; tc++) {

            int start_r = tr * T;
            int start_c = tc * T;

            float tile_flat[16 * 16]; // T*T <= 256
            extract_tile_flat(image_flat, N, start_r, start_c, T, tile_flat);

            float act = pipeline_process_tile_streaming(tile_flat, depth, T, kernel);
            output_flat[tr * out_dim + tc] = act;
        }
    }
}

// ============================================================
// BRIDGE FUNCTION FOR PYTHON (correct: wrapper only)
// ============================================================
#ifdef __cplusplus
extern "C" {
#endif

    EXPORT void run_c_pipeline_bridge(
        float* input_flat,
        int N,
        float* kernel_flat,
        float* output_flat,
        int* out_dim_result
    ) {
        // Fix kernel mapping for 2x2: indices 0..3
        // (row-major): [k00, k01, k10, k11]
        float kernel[2][2];
        kernel[0][0] = kernel_flat[0];
        kernel[0][1] = kernel_flat[1];
        kernel[1][0] = kernel_flat[2];
        kernel[1][1] = kernel_flat[3];

        // Run the fused pipeline end-to-end
        process_full_image_without_fc_flat(input_flat, N, kernel, output_flat, out_dim_result);
    }

#ifdef __cplusplus
}
#endif
// ============================================================
// TEST MAIN (for debugging the C code)
// ============================================================

int main() {

    printf("HELLO FROM MAIN\n");
    int N = 32;

    float input_flat[32 * 32];
    float kernel_flat[4];
    float output_flat[32 * 32];

    int out_dim = 0;

    // ------------------------------------------------------------
    // Initialize input to zeros
    // ------------------------------------------------------------
    for (int i = 0; i < 32 * 32; i++) {
        input_flat[i] = 0.0f;
    }

    // ------------------------------------------------------------
    // Put ones in the top-left 2x2 tile
    // ------------------------------------------------------------
    input_flat[0 * 32 + 0] = 1.0f;
    input_flat[0 * 32 + 1] = 1.0f;
    input_flat[1 * 32 + 0] = 1.0f;
    input_flat[1 * 32 + 1] = 1.0f;

    // ------------------------------------------------------------
    // Kernel = all ones
    // ------------------------------------------------------------
    kernel_flat[0] = 1.0f;
    kernel_flat[1] = 1.0f;
    kernel_flat[2] = 1.0f;
    kernel_flat[3] = 1.0f;

    // ------------------------------------------------------------
    // Clear output
    // ------------------------------------------------------------
    for (int i = 0; i < 32 * 32; i++) {
        output_flat[i] = 0.0f;
    }

    // ------------------------------------------------------------
    // Run your pipeline
    // ------------------------------------------------------------
    run_c_pipeline_bridge(
        input_flat,
        N,
        kernel_flat,
        output_flat,
        &out_dim
    );

    // ------------------------------------------------------------
    // Print output dimension
    // ------------------------------------------------------------
    printf("Output dimension: %d\n\n", out_dim);

    // ------------------------------------------------------------
    // Print output matrix
    // ------------------------------------------------------------
    for (int r = 0; r < out_dim; r++) {
        for (int c = 0; c < out_dim; c++) {
            printf("%6.1f ", output_flat[r * out_dim + c]);
        }
        printf("\n");
    }

    return 0;
}