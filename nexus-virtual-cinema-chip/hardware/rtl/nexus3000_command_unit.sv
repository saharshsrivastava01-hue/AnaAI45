// Minimal command sequencer: accepts one command and emits a one-cycle issue pulse.
// opcode 0 = vector MAC, 1 = ReLU, others = illegal.
module nexus3000_command_unit(
  input logic clk, input logic rst_n,
  input logic cmd_valid, output logic cmd_ready,
  input logic [7:0] cmd_opcode, input logic [15:0] cmd_tag,
  output logic issue_valid, input logic issue_ready,
  output logic [1:0] issue_opcode, output logic [15:0] issue_tag,
  output logic illegal_opcode
);
  logic held;
  assign cmd_ready=!held;
  always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
      held<=0; issue_valid<=0; issue_opcode<=0; issue_tag<=0; illegal_opcode<=0;
    end else begin
      illegal_opcode<=0;
      if(cmd_valid && cmd_ready) begin
        if(cmd_opcode<=1) begin
          issue_opcode<=cmd_opcode[1:0]; issue_tag<=cmd_tag;
          issue_valid<=1; held<=1;
        end else begin illegal_opcode<=1; end
      end else if(issue_valid && issue_ready) begin
        issue_valid<=0; held<=0;
      end
    end
  end
endmodule
