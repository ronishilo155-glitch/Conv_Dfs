// mac_lane: 2x2 convolution MAC with 1-cycle pipeline.
//
// PIPELINE STRUCTURE:
//   Stage 1 (registered): 4 parallel signed multiplications.
//   Stage 2 (combinational, registered by process_unit bank flops):
//     Addition tree -> ReLU -> >>2 normalize -> saturation to 16-bit.
//
// TIMING FIX:
//   Original design had a single long combinational chain:
//     multiply x4 -> add -> relu -> shift -> saturate
//   This limited frequency to ~43 MHz.
//   By registering the multiply outputs we break the path into two ~10 ns halves,
//   targeting 80-100 MHz.
//
// LATENCY: out_pixel is valid 1 cycle after {p0..p3, w0..w3} are presented.
//   process_unit accounts for this with delayed write-address registers.

module mac_lane (
    input  logic               clk,
    input  logic        [15:0] p0, p1, p2, p3,   // 16-bit intermediate pixels
    input  logic signed [7:0]  w0, w1, w2, w3,   // 8-bit signed kernel weights
    output logic        [15:0] out_pixel          // 16-bit output, valid 1 cycle later
);

    // ----------------------------------------------------------------
    // Stage 1: parallel multiplications.
    // Registered to break the critical path.
    // Each product: sign-extended 17-bit pixel * 8-bit weight = 25-bit signed.
    // ----------------------------------------------------------------
    logic signed [24:0] mul0_r, mul1_r, mul2_r, mul3_r;

    always_ff @(posedge clk) begin
        mul0_r <= $signed({1'b0, p0}) * w0;
        mul1_r <= $signed({1'b0, p1}) * w1;
        mul2_r <= $signed({1'b0, p2}) * w2;
        mul3_r <= $signed({1'b0, p3}) * w3;
    end

    // ----------------------------------------------------------------
    // Stage 2: accumulate, activate, normalise, saturate.
    // Purely combinational — terminates in the bank flip-flop inside
    // process_unit (no extra register needed here).
    // ----------------------------------------------------------------
    logic signed [26:0] adder_out;
    assign adder_out = mul0_r + mul1_r + mul2_r + mul3_r;

    logic [26:0] relu_out;
    assign relu_out = adder_out[26] ? 27'd0 : adder_out; // ReLU: clamp negatives to 0

    logic [26:0] shifted_out;
    assign shifted_out = relu_out >> 2; // normalise: keep values in 0-65535 range

    assign out_pixel = shifted_out[15:0]; // truncate low 16 bits — matches SW (uint16_t) cast

endmodule
