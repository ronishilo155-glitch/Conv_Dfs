// process_unit: tile-based fused Conv+ReLU+Normalize pipeline.
//
// PIPELINE ADAPTATION:
//   mac_lane now has 1-cycle latency (registered multiply stage).
//   To compensate, write-address signals (write_bank, write_idx, write_to_A)
//   are registered by 1 cycle, so the bank write uses the address from
//   the cycle in which the inputs were presented.
//
//   DONE signalling: asserted the cycle after the last bank write
//   (1 cycle drain after is_working falls).
//
// TIMING FIX (from process_unit side):
//   Replaced modulo-2 with XOR of LSBs (0 LEs).
//   Replaced out_N*out_N with a case table (no multiplier).

module process_unit (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        start,
    input  logic [31:0] kernel_reg,
    input  logic [2:0]  current_depth,
    input  logic [2:0]  initial_depth,
    input  logic [7:0]  load_buffer [0:255],

    output logic        done,
    output logic [15:0] final_pixel_out
);

    // ----------------------------------------------------------------
    // Ping-pong memory banks: spatially interleaved for 4-pixel parallel read.
    // ----------------------------------------------------------------
    (* ramstyle = "M9K" *) logic [15:0] bufA_00 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufA_01 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufA_10 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufA_11 [0:63];

    (* ramstyle = "M9K" *) logic [15:0] bufB_00 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufB_01 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufB_10 [0:63];
    (* ramstyle = "M9K" *) logic [15:0] bufB_11 [0:63];

    logic last_written_to_A;
    assign final_pixel_out = last_written_to_A ? bufA_00[0] : bufB_00[0];

    // FIX: replace (initial_depth - current_depth) % 2 == 0 with XOR of LSBs.
    logic write_to_A;
    assign write_to_A = ~(initial_depth[0] ^ current_depth[0]);

    // ----------------------------------------------------------------
    // MAC lane instantiation — now pipelined (1 cycle latency).
    // ----------------------------------------------------------------
    logic [15:0] p_in [0:3];
    logic [15:0] mac_out;

    mac_lane mac_inst (
        .clk    (clk),
        .p0     (p_in[0]),
        .p1     (p_in[1]),
        .p2     (p_in[2]),
        .p3     (p_in[3]),
        .w0     (kernel_reg[7:0]),
        .w1     (kernel_reg[15:8]),
        .w2     (kernel_reg[23:16]),
        .w3     (kernel_reg[31:24]),
        .out_pixel(mac_out)
    );

    // ----------------------------------------------------------------
    // Output pixel count per stage (case table, no multiplier).
    // ----------------------------------------------------------------
    // out_idx declared before the always_comb blocks that reference it.
    logic [7:0] out_idx;
    logic [7:0] out_N;
    logic [7:0] total_blocks;

    always_comb begin
        case (current_depth)
            3'd1: begin out_N = 8'd1;  total_blocks = 8'd1;  end
            3'd2: begin out_N = 8'd2;  total_blocks = 8'd4;  end
            3'd3: begin out_N = 8'd4;  total_blocks = 8'd16; end
            3'd4: begin out_N = 8'd8;  total_blocks = 8'd64; end
            default: begin out_N = 8'd1; total_blocks = 8'd1; end
        endcase
    end

    // Output coordinates from linear index.
    logic [3:0] out_r, out_c;
    always_comb begin
        case (out_N)
            8'd8: begin out_r = {1'b0, out_idx[5:3]}; out_c = {1'b0, out_idx[2:0]}; end
            8'd4: begin out_r = {2'd0, out_idx[3:2]}; out_c = {2'd0, out_idx[1:0]}; end
            8'd2: begin out_r = {3'd0, out_idx[1]};   out_c = {3'd0, out_idx[0]};   end
            8'd1: begin out_r = 4'd0;                 out_c = 4'd0;                 end
            default: begin out_r = 4'd0; out_c = 4'd0; end
        endcase
    end

    // 2x2 input block top-left coordinates.
    logic [3:0] r0, r1, c0, c1;
    assign r0 = {out_r[2:0], 1'b0};
    assign r1 = {out_r[2:0], 1'b1};
    assign c0 = {out_c[2:0], 1'b0};
    assign c1 = {out_c[2:0], 1'b1};

    // Bank read index for interleaved access.
    logic [5:0] read_idx;
    assign read_idx = {out_r[2:0], out_c[2:0]};

    // Load-buffer addresses (bit concatenation: 0 LEs).
    logic [7:0] addr00, addr01, addr10, addr11;
    assign addr00 = {r0[3:0], c0[3:0]};
    assign addr01 = {r0[3:0], c1[3:0]};
    assign addr10 = {r1[3:0], c0[3:0]};
    assign addr11 = {r1[3:0], c1[3:0]};

    // Parallel 4-pixel read: select source based on current pipeline depth.
    always_comb begin
        if (current_depth == initial_depth) begin
            p_in[0] = {8'h00, load_buffer[addr00]};
            p_in[1] = {8'h00, load_buffer[addr01]};
            p_in[2] = {8'h00, load_buffer[addr10]};
            p_in[3] = {8'h00, load_buffer[addr11]};
        end else if (!write_to_A) begin
            p_in[0] = bufA_00[read_idx];
            p_in[1] = bufA_01[read_idx];
            p_in[2] = bufA_10[read_idx];
            p_in[3] = bufA_11[read_idx];
        end else begin
            p_in[0] = bufB_00[read_idx];
            p_in[1] = bufB_01[read_idx];
            p_in[2] = bufB_10[read_idx];
            p_in[3] = bufB_11[read_idx];
        end
    end

    // Write routing: bank selector and index within bank.
    logic [1:0] write_bank;
    logic [5:0] write_idx;
    assign write_bank = {out_r[0], out_c[0]};
    assign write_idx  = {out_r[3:1], out_c[3:1]};

    // ----------------------------------------------------------------
    // Pipeline delay registers for write address.
    // Because mac_lane has 1-cycle latency, the write address must be
    // captured at the same time as the inputs and used one cycle later.
    // ----------------------------------------------------------------
    logic [1:0] write_bank_d;
    logic [5:0] write_idx_d;
    logic       write_to_A_d;

    // ----------------------------------------------------------------
    // FSM state.
    // prev_is_working: delayed version of is_working.
    //   Asserted during the cycle in which mac_out is valid and a
    //   bank write should occur.
    // ----------------------------------------------------------------
    logic       is_working;
    logic       prev_is_working;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            is_working        <= 1'b0;
            prev_is_working   <= 1'b0;
            done              <= 1'b0;
            out_idx           <= '0;
            last_written_to_A <= 1'b0;
            write_bank_d      <= '0;
            write_idx_d       <= '0;
            write_to_A_d      <= 1'b0;
        end else begin

            // ---- pipeline delay registers (capture addresses for next cycle) ----
            write_bank_d    <= write_bank;
            write_idx_d     <= write_idx;
            write_to_A_d    <= write_to_A;
            prev_is_working <= is_working;

            // ---- done = 1 cycle after last write (pipeline drain) ----
            // prev_is_working just fell (last mac_out written this cycle).
            done <= prev_is_working && !is_working;

            // ---- computation control ----
            if (start && !is_working) begin
                is_working <= 1'b1;
                out_idx    <= '0;
            end else if (is_working) begin
                if (out_idx == total_blocks - 1) begin
                    is_working <= 1'b0;  // stop feeding inputs; 1 drain cycle follows
                end else begin
                    out_idx <= out_idx + 1;
                end
            end

            // ---- bank write: use pipeline-delayed address, mac_out from stage 2 ----
            if (prev_is_working) begin
                last_written_to_A <= write_to_A_d;
                if (write_to_A_d) begin
                    if (write_bank_d == 2'b00) bufA_00[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b01) bufA_01[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b10) bufA_10[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b11) bufA_11[write_idx_d] <= mac_out;
                end else begin
                    if (write_bank_d == 2'b00) bufB_00[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b01) bufB_01[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b10) bufB_10[write_idx_d] <= mac_out;
                    if (write_bank_d == 2'b11) bufB_11[write_idx_d] <= mac_out;
                end
            end

        end
    end

endmodule
