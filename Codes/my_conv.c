#include <k5_libs.h>

/****************************** MACROS ******************************/

// NOTICE following must be compliant with the relative used address in the accelerator code, this is NOT automated.

// XBOX APB REGISTERS ADDRESS MACROS

#define CONV_REGS_BASE_IDX 0

#define CONV_INPUT_ADDR_REG_IDX  (CONV_REGS_BASE_IDX + 0) 
#define CONV_KERNEL_ADDR_REG_IDX (CONV_REGS_BASE_IDX + 1)
#define CONV_OUTPUT_ADDR_REG_IDX (CONV_REGS_BASE_IDX + 2) 
#define CONV_START_REG_IDX       (CONV_REGS_BASE_IDX + 3) 
#define CONV_DONE_REG_IDX        (CONV_REGS_BASE_IDX + 4) 

#define CONV_INPUT_ADDR_REG  ((volatile unsigned int *) (XBOX_REGS_BASE_ADDR + (4*CONV_INPUT_ADDR_REG_IDX))) 
#define CONV_KERNEL_ADDR_REG ((volatile unsigned int *) (XBOX_REGS_BASE_ADDR + (4*CONV_KERNEL_ADDR_REG_IDX))) 
#define CONV_OUTPUT_ADDR_REG ((volatile unsigned int *) (XBOX_REGS_BASE_ADDR + (4*CONV_OUTPUT_ADDR_REG_IDX))) 
#define CONV_START_REG       ((volatile unsigned int *) (XBOX_REGS_BASE_ADDR + (4*CONV_START_REG_IDX))) 
#define CONV_DONE_REG        ((volatile unsigned int *) (XBOX_REGS_BASE_ADDR + (4*CONV_DONE_REG_IDX))) 

//---------------------------------------------------------------------------------------------

// Configuration Structure

typedef struct conv_config {
    unsigned char * input_addr;
    unsigned char * kernel_addr;
    unsigned char * output_addr;
    
    int input_num_bytes;
    int kernel_num_bytes;
    int output_num_bytes;
    
    int input_height;
    int input_width;
    int kernel_size;
    int stride;
    int padding;
} conv_config_t;

//---------------------------------------------------------------------------------------------

void dump_conv_output(int dump_f, conv_config_t* conv_config_p) {
   
   bm_printf("Dumping convolution output at address: 0x%08x , byte length %d (decimal)\n", conv_config_p->output_addr, conv_config_p->output_num_bytes);
   // Starting a SOC level file to memory copy transfer
   int num_bytes_per_output_line = 32 ;
   bm_start_soc_store_hex_file (dump_f, conv_config_p->output_num_bytes, num_bytes_per_output_line, conv_config_p->output_addr) ;  // Store to dump file
   // Polling till transfer completed (SW may also do other stuff mean while)
   int num_dumped = 0 ;
   while (num_dumped==0) {
       num_dumped = bm_check_soc_store_hex_file () ; // num_dumped!=0 indicates completion.
   }
   bm_printf("Dumped %d bytes\n",num_dumped) ; 
}

//---------------------------------------------------------------------------------------------

void dump_cycle_count(int cycles_f, int cycle_count) {
   
   bm_printf("Dumping cycle count: %d\n", cycle_count);
   
   // Convert int to 4 bytes (little endian)
   unsigned char cycle_bytes[4];
   cycle_bytes[0] = (cycle_count >> 0) & 0xFF;
   cycle_bytes[1] = (cycle_count >> 8) & 0xFF;
   cycle_bytes[2] = (cycle_count >> 16) & 0xFF;
   cycle_bytes[3] = (cycle_count >> 24) & 0xFF;
   
   int num_bytes_per_output_line = 4 ;
   bm_start_soc_store_hex_file (cycles_f, 4, num_bytes_per_output_line, cycle_bytes) ;
   
   int num_dumped = 0 ;
   while (num_dumped==0) {
       num_dumped = bm_check_soc_store_hex_file () ;
   }
   bm_printf("Dumped cycle count\n");
}

//---------------------------------------------------------------------------------------------

void load_conv_config(int conv_config_f, conv_config_t *conv_config_p) { 
                        
   bm_printf("\nLoading Configuration file\n\n");
   // Starting a SOC level file to memory copy transfer
   bm_start_soc_load_hex_file (conv_config_f, sizeof(conv_config_t), (unsigned char *)conv_config_p) ; 
   // Polling till transfer completed (SW may also do other stuff mean while)
   int num_loaded = 0 ;
   while (num_loaded==0) num_loaded = bm_check_soc_load_hex_file () ; // num_loaded!=0 indicates completion.
   bm_printf("Loaded %d bytes\n",num_loaded) ;
   bm_printf("input_addr: 0x%08x\n",conv_config_p->input_addr);
   bm_printf("kernel_addr: 0x%08x\n",conv_config_p->kernel_addr);
   bm_printf("output_addr: 0x%08x\n",conv_config_p->output_addr);
   bm_printf("input_num_bytes: 0x%08x (%d decimal)\n",conv_config_p->input_num_bytes,conv_config_p->input_num_bytes);
   bm_printf("kernel_num_bytes: 0x%08x (%d decimal)\n\n",conv_config_p->kernel_num_bytes,conv_config_p->kernel_num_bytes);
}

//-----------------------------------------------------------------------------------------------

void load_conv_input(int data_f, conv_config_t *conv_config_p) { 
                      
   bm_printf("Loading input data: to address 0x%08x , byte length : %d\n", conv_config_p->input_addr, conv_config_p->input_num_bytes);
   bm_start_soc_load_hex_file (data_f, conv_config_p->input_num_bytes, conv_config_p->input_addr) ; 
   // Polling till transfer completed (SW may also do other stuff mean while)
   int num_loaded = 0 ;
   while (num_loaded==0) num_loaded = bm_check_soc_load_hex_file () ; // num_loaded!=0 indicates completion.
   bm_printf("Loaded %d bytes\n",num_loaded) ;
}

//---------------------------------------------------------------------------------------------

void load_conv_kernels(int kernel_f, conv_config_t *conv_config_p) { 
                      
   bm_printf("Loading kernel data: to address 0x%08x , byte length : %d\n", conv_config_p->kernel_addr, conv_config_p->kernel_num_bytes);
   bm_start_soc_load_hex_file (kernel_f, conv_config_p->kernel_num_bytes, conv_config_p->kernel_addr) ; 
   // Polling till transfer completed (SW may also do other stuff mean while)
   int num_loaded = 0 ;
   while (num_loaded==0) num_loaded = bm_check_soc_load_hex_file () ; // num_loaded!=0 indicates completion.
   bm_printf("Loaded %d bytes\n",num_loaded) ;
}

//---------------------------------------------------------------------------------------------

// Non accelerated reference — placeholder, copies input to output

void convolution_nox(conv_config_t *conv_config_p) {
   for (int i = 0; i < conv_config_p->output_num_bytes; i++) {
      conv_config_p->output_addr[i] = conv_config_p->input_addr[i];
   }
}

//---------------------------------------------------------------------------------------------

// ------------------------------------------------------------
// Compute pipeline depth:
// counts how many times we can halve N until N <= 16
// ------------------------------------------------------------
static int compute_depth_bm(int N) {
    int depth = 0;
    while (N > 16) {
        N >>= 1;
        depth++;
    }
    return depth;
}

// ------------------------------------------------------------
// ReLU activation: returns x if positive, else 0
// ------------------------------------------------------------
static inline int relu_bm(int x) { return (x > 0) ? x : 0; }

// ------------------------------------------------------------
// One stage of 2x2 conv stride-2 + ReLU + normalize (no malloc)
// in:  n*n flat buffer
// out: (n/2)*(n/2) flat buffer
// k:   kernel [k00, k01, k10, k11]
// >>1: normalize to prevent value overflow between stages
// ------------------------------------------------------------
static void conv2x2_stage_flat_bm(
    const unsigned char* in,
    int n,
    const int k[4],
    unsigned char* out
) {
    int out_size = n >> 1;
    int r, c;
    for (r = 0; r < out_size; r++) {
        int br = r << 1;
        for (c = 0; c < out_size; c++) {
            int bc = c << 1;
            int a  = (int) in[ br      * n + bc    ];
            int b  = (int) in[ br      * n + bc + 1];
            int c1 = (int) in[(br + 1) * n + bc    ];
            int d  = (int) in[(br + 1) * n + bc + 1];
            int acc = a * k[0] + b * k[1] + c1 * k[2] + d * k[3];
            acc = relu_bm(acc);  // Fusion: Conv + Activation
            //acc >>= 1;           // Normalize to keep values in 0-255 range
            out[r * out_size + c] = (unsigned char) acc;
        }
    }
}

// ------------------------------------------------------------
// Extract a tile from the full image into a flat buffer
// Single memory access per pixel — no further memory access during pipeline
// tile_flat size must be T*T
// image_flat is N*N: image_flat[r*N + c]
// ------------------------------------------------------------
static void extract_tile_flat_bm(
    const unsigned char* image_flat,
    int N,
    int start_r,
    int start_c,
    int T,
    unsigned char* tile_flat
) {
    int r, c;
    for (r = 0; r < T; r++) {
        for (c = 0; c < T; c++) {
            tile_flat[r * T + c] = image_flat[(start_r + r) * N + (start_c + c)];
        }
    }
}

// ------------------------------------------------------------
// Streaming fused pipeline for ONE tile (no malloc)
// Uses two fixed buffers and swaps pointers each stage
// No main memory access between stages — all computation in bufA/bufB
// Assumes T <= 16
// ------------------------------------------------------------
static unsigned char pipeline_process_tile_streaming_bm(
    const unsigned char* tile_flat,
    int depth,
    int T,
    const int kernel[4]
) {
    unsigned char bufA[16 * 16];
    unsigned char bufB[16 * 16];
    int i;
    for (i = 0; i < T * T; i++) bufA[i] = tile_flat[i];

    int cur = T;
    unsigned char* in  = bufA;
    unsigned char* out = bufB;

    int stage;
    for (stage = 0; stage < depth; stage++) {
        conv2x2_stage_flat_bm(in, cur, kernel, out);
        cur >>= 1;
        // Swap buffers — no memory allocation needed
        unsigned char* tmp = in; in = out; out = tmp;
    }
    // After depth stages, cur == 1, result is in in[0]
    return in[0];
}

// ------------------------------------------------------------
// Full image processing (no malloc)
// Splits image into tiles of size T*T
// Each tile goes through the full pipeline independently
// output: out_dim*out_dim where out_dim = N/T
// ------------------------------------------------------------
static void process_full_image_bm(
    const unsigned char* image_flat,
    int N,
    const int kernel[4],
    unsigned char* output_flat,
    int* out_dim_result
) {
    int depth   = compute_depth_bm(N);
    int T       = 1 << depth;   // Tile size = 2^depth
    int out_dim = N >> depth;   // Output dimension = N/T
    if (out_dim_result) *out_dim_result = out_dim;

    int tr, tc;
    for (tr = 0; tr < out_dim; tr++) {
        for (tc = 0; tc < out_dim; tc++) {
            int start_r = tr * T;
            int start_c = tc * T;

            // Extract tile from main memory — only memory access per tile
            unsigned char tile_flat[16 * 16];
            extract_tile_flat_bm(image_flat, N, start_r, start_c, T, tile_flat);

            // Process tile through full pipeline — no main memory access
            unsigned char act = pipeline_process_tile_streaming_bm(
                                    tile_flat, depth, T, kernel);
            // Write result to output — only memory write per tile
            output_flat[tr * out_dim + tc] = act;
        }
    }
}

// ------------------------------------------------------------
// Accelerated convolution entry point
// Reads addresses and kernel from conv_config
// Runs the full fused pipeline
// ------------------------------------------------------------
void convolution_xlr(conv_config_t *conv_config_p) {

    unsigned char* image_flat  = conv_config_p->input_addr;
    unsigned char* kernel_flat = conv_config_p->kernel_addr;
    unsigned char* output_flat = conv_config_p->output_addr;

    // Load 2x2 kernel as integers [k00, k01, k10, k11]
    int kernel[4];
    kernel[0] = (int) kernel_flat[0];
    kernel[1] = (int) kernel_flat[1];
    kernel[2] = (int) kernel_flat[2];
    kernel[3] = (int) kernel_flat[3];

    int N = conv_config_p->input_width;
    int out_dim;

    process_full_image_bm(image_flat, N, kernel, output_flat, &out_dim);
}

//-----------------------------------------------------------------------------------------------

void run_convolution(conv_config_t *conv_config_p, boolean is_xlr_enabled, int *cycle_count) {
    
   bm_printf("Starting convolution of %d bytes from addr 0x%08x to addr 0x%08x\n", 
              conv_config_p->input_num_bytes, conv_config_p->input_addr, conv_config_p->output_addr);

   // Performance time stamping initialize 
   //int start_cycle,end_cycle ;            // For performance checking.  
   //ENABLE_CYCLE_COUNT ;                   // Enable the cycle counter
   //RESET_CYCLE_COUNT  ;                   // Reset counter to ensure 32 bit counter does not wrap in-between start and end.   
   //GET_CYCLE_COUNT_START(start_cycle) ;   // Capture the cycle count before the operation.

   bm_printf("%d",is_xlr_enabled);
   if (is_xlr_enabled) convolution_xlr(conv_config_p); 
   else                convolution_nox(conv_config_p);

   // Performance time stamping report
   //GET_CYCLE_COUNT_END(end_cycle) ;  // Capture the cycle count after the operation.
   //*cycle_count = end_cycle-start_cycle ; // Calculate consumed cycles.  

   //#ifndef XON
   //*cycle_count = (*cycle_count)/8 ; // Factor single thread mode (Other 7 threads unutilized)
   //#endif

   *cycle_count=1;
   //bm_printf("\n\n *** Measured execution time: %d K5 effective cycles ***\n\n",*cycle_count); // Report
}

//-----------------------------------------------------------------------------------------------

int main() {
  
   bm_printf("\nHELLO CONVOLUTION REFERENCE\n"); 

   //char gen_test_per_run=FALSE ;
   //#ifdef REGEN
   //gen_test_per_run = TRUE ;
   //#endif 
   char gen_test_per_run=TRUE ;
  
   if (gen_test_per_run) {
      bm_printf("\nSystem call for generating a random test case\n") ;
      bm_sys_call("python3 app_src_dir/gen_conv_test.py");
   }
   else {
      bm_printf("\nNew test not generated, you may generate new test from runspace prompt by:\n") ;
      bm_printf("python3 app_src_dir/gen_conv_test.py\n") ;
   }

   int input_f      = bm_fopen_r("conv_input.txt") ;        // Generated test input data
   int kernel_f     = bm_fopen_r("conv_kernels.txt") ;      // Generated test kernel data
   int conv_config_f = bm_fopen_r("conv_config.txt") ;      // Generated test configuration
   int output_f     = bm_fopen_w("conv_output.txt") ;       // Output file generated at run space
   int cycles_f     = bm_fopen_w("conv_cycles.txt") ;       // Cycle count output file

   conv_config_t conv_config ;
  
   boolean is_xlr_enabled = TRUE; // Is Accelerator Enabled, default (can be changed)
   // Overwrite default controlled from shell invocation line 

   #ifdef XON
   is_xlr_enabled = TRUE ;
   #endif 
   #ifdef XOFF
   is_xlr_enabled = FALSE ;
   #endif
  
   if (is_xlr_enabled) bm_printf("\nAccelerator Enabled\n") ;
   else bm_printf("\nAccelerator Disabled\n") ;
    
   load_conv_config(conv_config_f, &conv_config) ; // Load Configuration info
   load_conv_input(input_f, &conv_config) ;         // Load input data
   load_conv_kernels(kernel_f, &conv_config) ;      // Load kernel data

   int cycle_count ;
   run_convolution(&conv_config, is_xlr_enabled, &cycle_count);

   dump_conv_output(output_f, &conv_config) ;
   dump_cycle_count(cycles_f, cycle_count) ;
  
   bm_fclose(input_f) ;  
   bm_fclose(kernel_f) ;
   bm_fclose(conv_config_f) ;     
   bm_fclose(output_f) ;
   bm_fclose(cycles_f) ;  

   bm_printf("\nCheck convolution results\n") ;
   bm_sys_call("python3 app_src_dir/process_conv_results.py");

   bm_quit_app() ;  // flag to trigger execution termination   
   return 0;
}

//-----------------------------------------------------------------------------------------------