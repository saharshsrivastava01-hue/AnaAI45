// NEXUS-3000 Chip Top v0.2
// Integrates command decode/tagging with the four-lane INT16 compute tile.
// This is a small synthesizable FPGA-oriented prototype, not a GPU/TPU.
module nexus3000_chip_top #(
  parameter int LANES = 4,
  parameter int DATA_W = 16,
  parameter int ACC_W = 40
) (
  input  logic clk,
  input  logic rst_n,

  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic [7:0] cmd_opcode,
  input  logic [15:0] cmd_tag,

  input  logic signed [LANES*DATA_W-1:0] vec_a,
  input  logic signed [LANES*DATA_W-1:0] vec_b,
  input  logic signed [ACC_W-1:0] acc_in,

  output logic rsp_valid,
  input  logic rsp_ready,
  output logic [15:0] rsp_tag,
  output logic signed [ACC_W-1:0] rsp_result,
  output logic rsp_error,
  output logic illegal_opcode
);
  logic issue_valid, issue_ready;
  logic [1:0] issue_opcode;
  logic [15:0] issue_tag;
  logic tile_valid, tile_ready, tile_error;
  logic signed [ACC_W-1:0] tile_result;
  logic [15:0] active_tag;

  nexus3000_command_unit u_command (
    .clk(clk), .rst_n(rst_n),
    .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
    .cmd_opcode(cmd_opcode), .cmd_tag(cmd_tag),
    .issue_valid(issue_valid), .issue_ready(issue_ready),
    .issue_opcode(issue_opcode), .issue_tag(issue_tag),
    .illegal_opcode(illegal_opcode)
  );

  nexus3000_compute_tile #(
    .LANES(LANES), .DATA_W(DATA_W), .ACC_W(ACC_W)
  ) u_compute (
    .clk(clk), .rst_n(rst_n),
    .req_valid(issue_valid), .req_ready(issue_ready),
    .opcode(issue_opcode), .vec_a(vec_a), .vec_b(vec_b), .acc_in(acc_in),
    .rsp_valid(tile_valid), .rsp_ready(rsp_ready),
    .result(tile_result), .error(tile_error)
  );

  // Capture the tag on the same cycle the command is accepted by the tile.
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      active_tag <= '0;
      rsp_tag <= '0;
    end else begin
      if (issue_valid && issue_ready)
        active_tag <= issue_tag;
      if (tile_valid && rsp_ready)
        rsp_tag <= active_tag;
    end
  end

  assign rsp_valid = tile_valid;
  assign rsp_result = tile_result;
  assign rsp_error = tile_error;
endmodule
