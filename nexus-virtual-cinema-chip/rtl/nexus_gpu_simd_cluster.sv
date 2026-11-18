// NEXUS-3000 Prototype B: small SIMD-style GPU execution cluster.
// Educational FPGA-oriented RTL. Not a production GPU.
module nexus_gpu_simd_cluster #(
  parameter int LANES=4, DATA_W=32
)(
  input logic clk, rst_n,
  input logic in_valid,
  output logic in_ready,
  input logic [2:0] opcode,
  input logic signed [DATA_W-1:0] a [LANES],
  input logic signed [DATA_W-1:0] b [LANES],
  output logic out_valid,
  input logic out_ready,
  output logic signed [DATA_W-1:0] result [LANES]
);
  localparam logic [2:0] OP_ADD=3'd0, OP_SUB=3'd1,
    OP_MUL_LO=3'd2, OP_AND=3'd3, OP_OR=3'd4,
    OP_XOR=3'd5, OP_MIN=3'd6, OP_MAX=3'd7;
  logic valid_q;
  logic signed [DATA_W-1:0] next_result [LANES];

  always_comb begin
    in_ready = !valid_q || out_ready;
    for (int i=0;i<LANES;i++) begin
      case (opcode)
        OP_ADD:    next_result[i] = a[i] + b[i];
        OP_SUB:    next_result[i] = a[i] - b[i];
        OP_MUL_LO: next_result[i] = a[i] * b[i];
        OP_AND:    next_result[i] = a[i] & b[i];
        OP_OR:     next_result[i] = a[i] | b[i];
        OP_XOR:    next_result[i] = a[i] ^ b[i];
        OP_MIN:    next_result[i] = (a[i] < b[i]) ? a[i] : b[i];
        default:   next_result[i] = (a[i] > b[i]) ? a[i] : b[i];
      endcase
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      valid_q <= 1'b0;
      for (int i=0;i<LANES;i++) result[i] <= '0;
    end else begin
      if (in_valid && in_ready) begin
        for (int i=0;i<LANES;i++) result[i] <= next_result[i];
        valid_q <= 1'b1;
      end else if (out_valid && out_ready) begin
        valid_q <= 1'b0;
      end
    end
  end
  assign out_valid=valid_q;
endmodule
