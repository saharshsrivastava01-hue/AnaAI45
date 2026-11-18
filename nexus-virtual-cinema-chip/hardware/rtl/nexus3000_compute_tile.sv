// NEXUS-3000 Compute Tile v0.1
// Synthesizable SystemVerilog starter: 4-lane signed INT16 vector MAC.
// This is a small FPGA-prototype compute tile, not a complete GPU/TPU.
module nexus3000_compute_tile #(
  parameter int LANES = 4,
  parameter int DATA_W = 16,
  parameter int ACC_W = 40
) (
  input  logic clk, input logic rst_n,
  input  logic req_valid, output logic req_ready,
  input  logic [1:0] opcode, // 00: vector MAC, 01: ReLU(vector A)
  input  logic signed [LANES*DATA_W-1:0] vec_a,
  input  logic signed [LANES*DATA_W-1:0] vec_b,
  input  logic signed [ACC_W-1:0] acc_in,
  output logic rsp_valid, input logic rsp_ready,
  output logic signed [ACC_W-1:0] result,
  output logic error
);
  logic busy;
  logic signed [ACC_W-1:0] calc;
  integer i;
  logic signed [DATA_W-1:0] a_lane, b_lane;
  always_comb begin
    calc = acc_in;
    error = 1'b0;
    case (opcode)
      2'b00: begin
        for (i=0; i<LANES; i=i+1) begin
          a_lane = $signed(vec_a[i*DATA_W +: DATA_W]);
          b_lane = $signed(vec_b[i*DATA_W +: DATA_W]);
          calc = calc + (a_lane * b_lane);
        end
      end
      2'b01: begin
        calc = '0;
        for (i=0; i<LANES; i=i+1) begin
          a_lane = $signed(vec_a[i*DATA_W +: DATA_W]);
          if (a_lane > 0) calc = calc + a_lane;
        end
      end
      default: begin calc = '0; error = 1'b1; end
    endcase
  end
  assign req_ready = !busy && (!rsp_valid || rsp_ready);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0; rsp_valid <= 1'b0; result <= '0;
    end else begin
      if (req_valid && req_ready) begin
        result <= calc;
        rsp_valid <= 1'b1;
        busy <= 1'b0;
      end else if (rsp_valid && rsp_ready) begin
        rsp_valid <= 1'b0;
      end
    end
  end
endmodule
