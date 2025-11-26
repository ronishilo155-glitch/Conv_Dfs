#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

//
// Global parameters for the project
//
#define MIN_DEPTH   0
#define MAX_DEPTH   4
#define K           2                     // kernel + stride = 2
#define MAX_INPUT_SIZE (1 << (MAX_DEPTH + 4))   // 256

//
// Utility: compute the input size for a given depth
// N = 2^(depth + 4)
//
int input_size_for_depth(int depth) {
    if (depth < MIN_DEPTH || depth > MAX_DEPTH) return -1;
    return 1 << (depth + 4);
}

//
// Infer depth from image size N (must be 16,32,64,128,256)
//
int infer_depth_from_size(int N) {
    for (int d = MIN_DEPTH; d <= MAX_DEPTH; ++d) {
        if (input_size_for_depth(d) == N)
            return d;
    }
    return -1;
}

//
// Validate that the given depth and image size match
//
int validate_depth_and_size(int depth, int H, int W) {
    if (depth < MIN_DEPTH || depth > MAX_DEPTH) {
        fprintf(stderr, "Error: depth %d out of range.\n", depth);
        return 0;
    }
    if (H != W) {
        fprintf(stderr, "Error: image must be square.\n");
        return 0;
    }
    int expected = input_size_for_depth(depth);
    if (H != expected) {
        fprintf(stderr, "Error: for depth %d input must be %dx%d.\n",
            depth, expected, expected);
        return 0;
    }
    return 1;
}

//
// Skip comments and whitespace inside a PGM file
//
static void skip_pgm_comments(FILE* fp) {
    int c = fgetc(fp);
    while (isspace(c)) c = fgetc(fp);

    while (c == '#') {
        while (c != '\n' && c != '\r' && c != EOF)
            c = fgetc(fp);
        c = fgetc(fp);
        while (isspace(c)) c = fgetc(fp);
    }
    if (c != EOF) ungetc(c, fp);
}

//
// Load a PGM (P2) grayscale file into a float buffer
//
int load_pgm_gray(const char* filename, float** out_buf, int* out_H, int* out_W) {
    FILE* fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "Cannot open file '%s'.\n", filename);
        return 0;
    }

    char magic[3] = { 0 };
    fscanf(fp, "%2s", magic);
    if (strcmp(magic, "P2") != 0) {
        fprintf(stderr, "Error: only P2 format supported.\n");
        fclose(fp);
        return 0;
    }

    skip_pgm_comments(fp);

    int W, H;
    fscanf(fp, "%d %d", &W, &H);

    skip_pgm_comments(fp);

    int maxval;
    fscanf(fp, "%d", &maxval);

    float* buf = (float*)malloc(sizeof(float) * W * H);
    if (!buf) {
        fprintf(stderr, "Malloc failed.\n");
        fclose(fp);
        return 0;
    }

    for (int i = 0; i < W * H; i++) {
        int pix;
        fscanf(fp, "%d", &pix);
        buf[i] = (float)pix;
    }

    fclose(fp);
    *out_buf = buf;
    *out_H = H;
    *out_W = W;
    return 1;
}

//
// Save buffer as PGM (P2)
//
int save_pgm_gray(const char* filename, const float* buf, int H, int W) {
    FILE* fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, "Cannot save output file.\n");
        return 0;
    }

    fprintf(fp, "P2\n");
    fprintf(fp, "# Output from LWCNN pipeline\n");
    fprintf(fp, "%d %d\n", W, H);
    fprintf(fp, "255\n");

    for (int i = 0; i < H * W; i++) {
        float v = buf[i];
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        fprintf(fp, "%d ", (int)(v + 0.5f));
        if ((i + 1) % W == 0) fprintf(fp, "\n");
    }

    fclose(fp);
    return 1;
}

//
// Single LWCNN convolution layer (no overlap)
//
void conv2d_LWCNN(
    const float* input,
    int C_in,
    int H,
    int W,
    const float* weights,
    const float* bias,
    int C_out,
    float* output
) {
    int stride = K;
    int H_out = H / K;
    int W_out = W / K;

#define IN(c,y,x)       input[(c)*H*W + (y)*W + (x)]
#define WGT(f,c,ky,kx)  weights[((f)*C_in + (c))*K*K + (ky)*K + (kx)]
#define OUT(f,y,x)      output[(f)*H_out*W_out + (y)*W_out + (x)]

    for (int f = 0; f < C_out; f++) {
        for (int oy = 0; oy < H_out; oy++) {
            for (int ox = 0; ox < W_out; ox++) {

                float sum = (bias ? bias[f] : 0.0f);

                int iy0 = oy * stride;
                int ix0 = ox * stride;

                for (int c = 0; c < C_in; c++) {
                    for (int ky = 0; ky < K; ky++) {
                        for (int kx = 0; kx < K; kx++) {
                            sum += IN(c, iy0 + ky, ix0 + kx) * WGT(f, c, ky, kx);
                        }
                    }
                }
                OUT(f, oy, ox) = sum;
            }
        }
    }

#undef IN
#undef WGT
#undef OUT
}

//
// Full pipeline — multiple LWCNN layers with ping–pong work buffers
//
void lwcnn_pipeline(
    const float* input0,
    int depth,
    const float* weights[],
    const float* biases[],
    float* workbuf1,
    float* workbuf2,
    float** final_output,
    int* H_last,
    int* W_last
) {
    int H = input_size_for_depth(depth);
    int W = H;

    const float* cur_in = input0;
    float* cur_out = workbuf1;

    for (int d = 0; d < depth; d++) {
        printf("Layer %d: input size %dx%d\n", d, H, W);

        conv2d_LWCNN(
            cur_in,
            1,        // C_in
            H, W,
            weights[d],
            biases[d],
            1,        // C_out
            cur_out
        );

        H /= K;
        W /= K;

        const float* next_in = cur_out;
        cur_out = (cur_out == workbuf1 ? workbuf2 : workbuf1);
        cur_in = next_in;
    }

    *final_output = (float*)cur_in;
    *H_last = H;
    *W_last = W;
}

//
// MAIN PROGRAM
//
int main() {
    printf("LWCNN Pipeline – starting.\n");

    // Load input image
    float* input = NULL;
    int H, W;
    if (!load_pgm_gray("input.pgm", &input, &H, &W)) {
        return 1;
    }
    printf("Loaded input image: %dx%d\n", H, W);

    // Infer depth from size
    int depth = infer_depth_from_size(H);
    if (depth < 0 || !validate_depth_and_size(depth, H, W)) {
        fprintf(stderr, "Invalid image size.\n");
        free(input);
        return 1;
    }

    // Allocate work buffers
    int max_elems = MAX_INPUT_SIZE * MAX_INPUT_SIZE;
    float* workbuf1 = (float*)malloc(sizeof(float) * max_elems);
    float* workbuf2 = (float*)malloc(sizeof(float) * max_elems);

    // Allocate weights & bias
    float* weights[MAX_DEPTH] = { 0 };
    float* biases[MAX_DEPTH] = { 0 };

    for (int d = 0; d < depth; d++) {
        weights[d] = (float*)malloc(sizeof(float) * 4);
        biases[d] = (float*)malloc(sizeof(float) * 1);

        for (int i = 0; i < 4; i++)
            weights[d][i] = 0.25f;

        biases[d][0] = 0.0f;
    }

    // Run pipeline
    float* final_out;
    int H_last, W_last;

    lwcnn_pipeline(
        input,
        depth,
        (const float**)weights,
        (const float**)biases,
        workbuf1,
        workbuf2,
        &final_out,
        &H_last,
        &W_last
    );

    printf("Pipeline finished. Final size = %dx%d\n", H_last, W_last);

    // Save output
    save_pgm_gray("output.pgm", final_out, H_last, W_last);

    // Cleanup
    free(input);
    free(workbuf1);
    free(workbuf2);

    for (int d = 0; d < depth; d++) {
        free(weights[d]);
        free(biases[d]);
    }

    return 0;
}
