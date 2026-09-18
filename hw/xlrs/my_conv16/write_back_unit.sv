module write_back_unit (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        start,            
    input  logic [7:0]  current_tile,     
    input  logic [7:0]  final_pixel,      
    input  logic [XMEM_ADDR_WIDTH-1:0] dst_addr_base, // The starting address for output
    
    // Memory Write Interface
    output logic        mem_req,
    output logic [XMEM_ADDR_WIDTH-1:0] mem_start_addr,
    output logic [7:0]  mem_data,         
    output logic [3:0]  mem_size_bytes,   
    input  logic        mem_done,         
    
    output logic        done,             
    output logic        is_last_tile,     
    output logic [7:0]  next_tile         
);

    // Internal state machine control
    logic is_writing;

    // ---------------------------------------------------------
    // Combinational Logic: Setting up the write
    // ---------------------------------------------------------
    assign mem_size_bytes = 4'd1;           // We always write exactly 1 byte
    assign mem_data       = final_pixel;    // Put the calculated pixel on the bus
    assign mem_start_addr = dst_addr_base + current_tile; // Calculate write address
    
    // Status signals
    assign is_last_tile = (current_tile == 8'd255);
    assign next_tile    = current_tile + 8'd1;

    // ---------------------------------------------------------
    // Sequential Logic: FSM for Memory Handshake
    // ---------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            is_writing <= 1'b0;
            mem_req    <= 1'b0;
            done       <= 1'b0;
        end else begin
            // Default pulse drop
            done <= 1'b0;

            if (start) begin
                is_writing <= 1'b1;
                mem_req    <= 1'b1; // Trigger the write to memory
            end 
            else if (is_writing && mem_done) begin
                is_writing <= 1'b0;
                mem_req    <= 1'b0; // Memory confirmed, drop request
                done       <= 1'b1; // Pulse 'done' for 1 cycle
            end
        end
    end

endmodule