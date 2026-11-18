// NEXUS-3000 on-chip scratchpad RAM (single synchronous read/write port).
// FPGA tools may infer block RAM depending on target and synthesis constraints.
module nexus3000_scratchpad #(
  parameter int DATA_W=32, ADDR_W=10
)(
  input logic clk, input logic rst_n,
  input logic req_valid, output logic req_ready,
  input logic req_write, input logic [ADDR_W-1:0] req_addr,
  input logic [DATA_W-1:0] req_wdata,
  output logic rsp_valid, input logic rsp_ready,
  output logic [DATA_W-1:0] rsp_rdata
);
  localparam int DEPTH=(1<<ADDR_W);
  logic [DATA_W-1:0] mem [0:DEPTH-1];
  logic pending;
  assign req_ready = !pending && (!rsp_valid || rsp_ready);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin pending<=1'b0; rsp_valid<=1'b0; rsp_rdata<='0; end
    else begin
      if (req_valid && req_ready) begin
        if (req_write) begin mem[req_addr]<=req_wdata; rsp_rdata<='0; end
        else rsp_rdata<=mem[req_addr];
        rsp_valid<=1'b1;
      end else if (rsp_valid && rsp_ready) rsp_valid<=1'b0;
    end
  end
endmodule
