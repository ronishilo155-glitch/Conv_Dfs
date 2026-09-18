module idle_unit (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       start_accel,  // 1-cycle pulse from the APB interface
    input  logic [8:0] n_size_reg,   // The image size N (e.g., 32, 64, 128, 256)
    output logic       done,         // 1-cycle pulse to trigger FSM transition
    output logic [2:0] initial_depth,
    output logic [7:0] pixels_in_tile
);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done           <= 1'b0;
            initial_depth  <= 3'd0;
            pixels_in_tile <= 8'd0;
        end else begin
            if (start_accel) begin
                // Decode the image size (N) to set pipeline depth and tile size.
                // pixels_in_tile is 0-based (Total - 1)
                case (n_size_reg)
                    9'd32:  begin initial_depth <= 3'd1; pixels_in_tile <= 8'd3;   end // 2x2
                    9'd64:  begin initial_depth <= 3'd2; pixels_in_tile <= 8'd15;  end // 4x4
                    9'd128: begin initial_depth <= 3'd3; pixels_in_tile <= 8'd63;  end // 8x8
                    9'd256: begin initial_depth <= 3'd4; pixels_in_tile <= 8'd255; end // 16x16
                    default:begin initial_depth <= 3'd0; pixels_in_tile <= 8'd0;   end
                endcase
                
                done <= 1'b1; // Assert 'done' for 1 clock cycle
            end else begin
                done <= 1'b0; // Drop the pulse
            end
        end
    end

endmodule