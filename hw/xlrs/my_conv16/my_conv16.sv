import xbox_def_pkg::*;

// Top-level accelerator FSM.
//
// CYCLE REDUCTION: Removed CHECK_DEPTH and WAIT_CHECK states.
// Depth check is now inlined in WAIT_PROC: when process_done, inspect
// depth_steps_left directly and branch to PROC_START or WRITE_BACK.
// Saves 2 cycles per depth stage x 4 stages x 256 tiles = 2,048 cycles.

module my_conv16 (
  input        clk,
  input        rst_n,

  input        [XBOX_NUM_REGS-1:0][31:0] host_regs,
  input  logic [XBOX_NUM_REGS-1:0]       host_regs_valid_pulse,
  output logic [XBOX_NUM_REGS-1:0][31:0] host_regs_data_out,
  output logic [XBOX_NUM_REGS-1:0]       host_regs_valid_out,
  input  logic [XBOX_NUM_REGS-1:0]       host_regs_read_pulse,

  mem_intf_read.client_read   mem_intf_read,
  mem_intf_write.client_write mem_intf_write
);

  // CHECK_DEPTH and WAIT_CHECK removed from state enum.
  typedef enum logic [3:0] {
      IDLE, WAIT_IDLE_UNIT,
      INIT_LOAD, WAIT_INIT_LOAD,
      PROC_START, WAIT_PROC,
      WRITE_BACK, WAIT_WRITE,
      SYNC_LOAD
  } state_t;
  state_t state, next_state;

  logic start_accel, accel_done;
  logic idle_done;
  logic [2:0] out_initial_depth;
  logic [7:0] out_pixels_in_tile;
  logic load_done;
  logic process_done;
  logic write_done, is_last_tile;
  logic [7:0] out_next_tile;

  logic [7:0]  load_to_process_buffer [0:255];
  logic [15:0] final_pixel_wire;

  logic [255:0] mem_read_data_tmp;
  assign mem_read_data_tmp = mem_intf_read.mem_data;

  logic [31:0][7:0] mem_write_data_tmp;
  always_comb begin
    mem_write_data_tmp = '0;
    if (state == WRITE_BACK || state == WAIT_WRITE)
        mem_write_data_tmp[0] = final_pixel_wire[7:0]; // truncate low 8 bits — matches SW reference
  end
  assign mem_intf_write.mem_data = mem_write_data_tmp;

  logic [8:0] load_tile_cnt;
  logic [8:0] proc_tile_cnt;
  logic [2:0] depth_steps_left;
  logic [7:0] pixels_in_tile;

  logic ping_pong_sel;
  logic load_is_done;
  logic load_triggered;

  logic start_load_pulse, start_process_pulse, start_write_pulse;

  enum {
     SRC_ADDR_IDX   = 0,
     DST_ADDR_IDX   = 1,
     N_SIZE_IDX     = 2,
     KERNEL_REG_IDX = 3,
     START_REG_IDX  = 4,
     DONE_REG_IDX   = 5
  } regs_idx;

  assign start_accel = host_regs[START_REG_IDX][0] && host_regs_valid_pulse[START_REG_IDX];

  logic [XBOX_NUM_REGS-1:0][31:0] host_regs_data_out_ps;
  always_comb begin
    host_regs_data_out_ps = host_regs_data_out;
    if (accel_done)
        host_regs_data_out_ps[DONE_REG_IDX][0] = 1'b1;
    else if (host_regs_read_pulse[DONE_REG_IDX])
        host_regs_data_out_ps[DONE_REG_IDX][0] = 1'b0;
    host_regs_valid_out = '0;
    host_regs_valid_out[DONE_REG_IDX] = host_regs_data_out[DONE_REG_IDX][0];
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) host_regs_data_out <= '0;
    else        host_regs_data_out <= host_regs_data_out_ps;
  end

  // Combinational next-state logic.
  always_comb begin
      next_state = state;
      accel_done = 1'b0;
      case (state)
          IDLE:          if (start_accel) next_state = WAIT_IDLE_UNIT;
          WAIT_IDLE_UNIT:if (idle_done)   next_state = INIT_LOAD;
          INIT_LOAD:     next_state = WAIT_INIT_LOAD;
          WAIT_INIT_LOAD:if (load_done)   next_state = PROC_START;
          PROC_START:    next_state = WAIT_PROC;

          // Inline depth check — no separate CHECK_DEPTH / WAIT_CHECK states.
          WAIT_PROC: if (process_done) begin
              if (depth_steps_left > 3'd1) next_state = PROC_START;
              else                         next_state = WRITE_BACK;
          end

          WRITE_BACK: next_state = WAIT_WRITE;
          WAIT_WRITE: if (write_done) next_state = SYNC_LOAD;

          SYNC_LOAD: begin
              if (load_is_done || load_tile_cnt == 9'd256) begin
                  if (proc_tile_cnt == 9'd255) begin
                      next_state = IDLE;
                      accel_done = 1'b1;
                  end else begin
                      next_state = PROC_START;
                  end
              end
          end
          default: next_state = IDLE;
      endcase
  end

  // Sequential logic.
  always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
          state               <= IDLE;
          load_tile_cnt       <= '0;
          proc_tile_cnt       <= '0;
          depth_steps_left    <= '0;
          pixels_in_tile      <= '0;
          ping_pong_sel       <= 1'b0;
          load_is_done        <= 1'b0;
          load_triggered      <= 1'b0;
          start_load_pulse    <= 1'b0;
          start_process_pulse <= 1'b0;
          start_write_pulse   <= 1'b0;
      end else begin
          state <= next_state;

          // Default: drop all pulses.
          start_load_pulse    <= 1'b0;
          start_process_pulse <= 1'b0;
          start_write_pulse   <= 1'b0;

          if (load_done) load_is_done <= 1'b1;

          case (state)
              IDLE: begin
                  load_tile_cnt  <= '0;
                  proc_tile_cnt  <= '0;
                  ping_pong_sel  <= 1'b0;
                  load_is_done   <= 1'b0;
                  load_triggered <= 1'b0;
              end
              WAIT_IDLE_UNIT: begin
                  if (idle_done) begin
                      pixels_in_tile   <= out_pixels_in_tile;
                      depth_steps_left <= out_initial_depth;
                  end
              end
              INIT_LOAD: begin
                  start_load_pulse <= 1'b1;
              end
              WAIT_INIT_LOAD: begin
                  if (load_done) begin
                      load_tile_cnt <= 9'd1;
                      proc_tile_cnt <= 9'd0;
                      ping_pong_sel <= 1'b1;
                      load_is_done  <= 1'b0;
                  end
              end
              PROC_START: begin
                  start_process_pulse <= 1'b1;
                  if (!load_triggered && load_tile_cnt < 9'd256) begin
                      start_load_pulse <= 1'b1;
                      load_triggered   <= 1'b1;
                  end
              end

              // Inline depth decrement: when looping back to PROC_START,
              // reduce depth here so process_unit sees depth-1 immediately.
              WAIT_PROC: begin
                  if (process_done && depth_steps_left > 3'd1)
                      depth_steps_left <= depth_steps_left - 3'd1;
              end

              WRITE_BACK: begin
                  start_write_pulse <= 1'b1;
              end
              SYNC_LOAD: begin
                  if (load_is_done || load_tile_cnt == 9'd256) begin
                      if (proc_tile_cnt < 9'd255) begin
                          proc_tile_cnt    <= proc_tile_cnt + 9'd1;
                          load_tile_cnt    <= load_tile_cnt + 9'd1;
                          ping_pong_sel    <= ~ping_pong_sel;
                          load_is_done     <= 1'b0;
                          load_triggered   <= 1'b0;
                          depth_steps_left <= out_initial_depth; // reset for next tile
                      end
                  end
              end
          endcase
      end
  end

  idle_unit i_idle (
      .clk            (clk),
      .rst_n          (rst_n),
      .start_accel    (start_accel && state == IDLE),
      .n_size_reg     (host_regs[N_SIZE_IDX][8:0]),
      .done           (idle_done),
      .initial_depth  (out_initial_depth),
      .pixels_in_tile (out_pixels_in_tile)
  );

  load_tile_unit i_load_tile (
      .clk            (clk),
      .rst_n          (rst_n),
      .start          (start_load_pulse),
      .buffer_sel     (ping_pong_sel),
      .n_size_reg     (host_regs[N_SIZE_IDX][8:0]),
      .initial_depth  (out_initial_depth),
      .src_addr_reg   (host_regs[SRC_ADDR_IDX][XMEM_ADDR_WIDTH-1:0]),
      .tile_cnt       (load_tile_cnt),
      .mem_req        (mem_intf_read.mem_req),
      .mem_start_addr (mem_intf_read.mem_start_addr),
      .mem_size_bytes (mem_intf_read.mem_size_bytes),
      .mem_valid      (mem_intf_read.mem_valid),
      .mem_data       (mem_read_data_tmp),
      .tile_buffer_out(load_to_process_buffer),
      .done           (load_done)
  );

  process_unit i_process (
      .clk             (clk),
      .rst_n           (rst_n),
      .start           (start_process_pulse),
      .kernel_reg      (host_regs[KERNEL_REG_IDX]),
      .current_depth   (depth_steps_left),
      .initial_depth   (out_initial_depth),
      .load_buffer     (load_to_process_buffer),
      .done            (process_done),
      .final_pixel_out (final_pixel_wire)
  );

  // check_depth_unit removed: depth check is now inlined in WAIT_PROC.

  logic [3:0] write_size_tmp;

  write_back_unit i_write_back (
      .clk           (clk),
      .rst_n         (rst_n),
      .start         (start_write_pulse),
      .current_tile  (proc_tile_cnt[7:0]),
      .final_pixel   (final_pixel_wire[7:0]),
      .dst_addr_base (host_regs[DST_ADDR_IDX][XMEM_ADDR_WIDTH-1:0]),
      .mem_req       (mem_intf_write.mem_req),
      .mem_start_addr(mem_intf_write.mem_start_addr),
      .mem_data      (),
      .mem_size_bytes(write_size_tmp),
      .mem_done      (mem_intf_write.mem_ack),
      .done          (write_done),
      .is_last_tile  (is_last_tile),
      .next_tile     (out_next_tile)
  );

  assign mem_intf_write.mem_size_bytes = {5'd0, write_size_tmp};

endmodule
