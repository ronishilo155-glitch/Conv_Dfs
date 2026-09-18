module check_depth_unit (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       start,            // 1-cycle trigger pulse
    input  logic [2:0] current_depth,    
    output logic       done,             // 1-cycle completion pulse
    output logic       needs_more_logic, 
    output logic [2:0] next_depth        
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done             <= 1'b0;
            needs_more_logic <= 1'b0;
            next_depth       <= 3'd0;
        end else begin
            if (start) begin
                needs_more_logic <= (current_depth > 3'd1);
                next_depth       <= (current_depth > 3'd1) ? (current_depth - 1) : current_depth;
                done             <= 1'b1; // Pulses high for 1 cycle
            end else begin
                done <= 1'b0; // Drops pulse
            end
        end
    end
endmodule