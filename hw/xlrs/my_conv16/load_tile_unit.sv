import xbox_def_pkg::*;

// Load Tile Unit
// Reads a tile of pixels from external memory into a ping-pong buffer.
//
// FIX: Replaced all hardware division and multiplication with bit-slicing
// and case statements (pure shift operations).
//
// Rationale:
//   tiles_per_row = N >> initial_depth = (16 << depth) >> depth = 16 always.
//   Therefore:
//     tile_r = tile_cnt / 16  =>  tile_r = tile_cnt[7:4]  (no divider needed)
//     tile_c = tile_cnt % 16  =>  tile_c = tile_cnt[3:0]  (no modulo needed)
//   Address offsets are powers-of-2 shifts, implemented as bit concatenation (0 LEs).

module load_tile_unit (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        start,
    input  logic        buffer_sel,
    input  logic [8:0]  n_size_reg,
    input  logic [2:0]  initial_depth,
    input  logic [XMEM_ADDR_WIDTH-1:0] src_addr_reg,
    input  logic [8:0]  tile_cnt,

    output logic        mem_req,
    output logic [XMEM_ADDR_WIDTH-1:0] mem_start_addr,
    output logic [8:0]  mem_size_bytes,
    input  logic        mem_valid,
    input  logic [255:0] mem_data,

    output logic [7:0]  tile_buffer_out [0:255],
    output logic        done
);

    typedef enum logic [1:0] {IDLE, REQ, WAIT_DATA} state_t;
    state_t state;

    logic [7:0] buf_0 [0:255];
    logic [7:0] buf_1 [0:255];
    assign tile_buffer_out = buffer_sel ? buf_0 : buf_1;

    // T = 2^initial_depth (power of 2; used as a shift, not a multiplier)
    logic [8:0] T;
    assign T = 9'd1 << initial_depth;

    // FIX 1: Replace division/modulo with bit slicing.
    // tiles_per_row is always 16, so:
    //   tile_r = tile_cnt / 16 = tile_cnt[7:4]
    //   tile_c = tile_cnt % 16 = tile_cnt[3:0]
    logic [3:0] tile_r;
    logic [3:0] tile_c;
    assign tile_r = tile_cnt[7:4];
    assign tile_c = tile_cnt[3:0];

    // FIX 2: Replace multiplications in base_addr with bit-concatenation shifts.
    // Formula: base = src + tile_r * T * N + tile_c * T
    // Since T=2^depth and N=16*T=2^(depth+4), all products are power-of-2 shifts:
    //   depth=1: tile_r*64  + tile_c*2
    //   depth=2: tile_r*256 + tile_c*4
    //   depth=3: tile_r*1024+ tile_c*8
    //   depth=4: tile_r*4096+ tile_c*16
    logic [31:0] base_addr;
    always_comb begin
        case (initial_depth)
            3'd1: base_addr = src_addr_reg + {tile_r, 6'b0} + {tile_c, 1'b0};
            3'd2: base_addr = src_addr_reg + {tile_r, 8'b0} + {tile_c, 2'b0};
            3'd3: base_addr = src_addr_reg + {tile_r, 10'b0} + {tile_c, 3'b0};
            3'd4: base_addr = src_addr_reg + {tile_r, 12'b0} + {tile_c, 4'b0};
            default: base_addr = src_addr_reg;
        endcase
    end

    logic [4:0] row_req;

    // FIX 3: Replace row_req * n_size_reg multiplication with bit-concatenation shift.
    // Since N=32,64,128,256 for depth=1,2,3,4 respectively:
    //   row_req * N = row_req << log2(N)
    logic [XMEM_ADDR_WIDTH-1:0] row_offset;
    always_comb begin
        case (initial_depth)
            3'd1: row_offset = {row_req, 5'b0};   // row_req * 32
            3'd2: row_offset = {row_req, 6'b0};   // row_req * 64
            3'd3: row_offset = {row_req, 7'b0};   // row_req * 128
            3'd4: row_offset = {row_req, 8'b0};   // row_req * 256
            default: row_offset = '0;
        endcase
    end
    assign mem_start_addr = base_addr[XMEM_ADDR_WIDTH-1:0] + row_offset;
    assign mem_size_bytes = T;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state   <= IDLE;
            row_req <= '0;
            done    <= 1'b0;
            mem_req <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        row_req <= '0;
                        state   <= REQ;
                    end
                end
                REQ: begin
                    mem_req <= 1'b1;
                    state   <= WAIT_DATA;
                end
                WAIT_DATA: begin
                    if (mem_valid) begin
                        mem_req <= 1'b0;

                        // Bit-concatenation addressing {row, col} prevents logic explosion.
                        // Unrolled loop: synthesis sees 16 constant-index assignments.
                        for (int i = 0; i < 16; i++) begin
                            if (i < T) begin
                                if (buffer_sel == 1'b0)
                                    buf_0[{row_req[3:0], i[3:0]}] <= mem_data[i*8 +: 8];
                                else
                                    buf_1[{row_req[3:0], i[3:0]}] <= mem_data[i*8 +: 8];
                            end
                        end

                        if (row_req == T - 1) begin
                            done  <= 1'b1;
                            state <= IDLE;
                        end else begin
                            row_req <= row_req + 1;
                            state   <= REQ;
                        end
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
