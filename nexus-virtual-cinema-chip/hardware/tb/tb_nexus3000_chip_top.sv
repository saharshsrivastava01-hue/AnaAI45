`timescale 1ns/1ps
module tb_nexus3000_chip_top;
  logic clk=0, rst_n=0;
  logic cmd_valid=0, cmd_ready;
  logic [7:0] cmd_opcode=0;
  logic [15:0] cmd_tag=0;
  logic signed [63:0] vec_a=0, vec_b=0;
  logic signed [39:0] acc_in=0;
  logic rsp_valid, rsp_ready=0;
  logic [15:0] rsp_tag;
  logic signed [39:0] rsp_result;
  logic rsp_error, illegal_opcode;
  always #5 clk=~clk;

  nexus3000_chip_top dut(.*);

  task automatic send(input logic [7:0] op, input logic [15:0] tag,
                      input logic signed [63:0] a, input logic signed [63:0] b,
                      input logic signed [39:0] acc);
    begin
      @(negedge clk);
      cmd_opcode=op; cmd_tag=tag; vec_a=a; vec_b=b; acc_in=acc; cmd_valid=1;
      do @(posedge clk); while (!cmd_ready);
      @(negedge clk); cmd_valid=0;
    end
  endtask

  initial begin
    repeat(2) @(negedge clk); rst_n=1;
    send(8'd0, 16'h1234,
         {16'sd4,16'sd3,16'sd2,16'sd1},
         {16'sd8,16'sd7,16'sd6,16'sd5}, 40'sd10);
    wait(rsp_valid);
    if (rsp_result !== 40'sd80) $fatal(1,"MAC expected 80 got %0d",rsp_result);
    if (rsp_tag !== 16'h1234) $fatal(1,"tag mismatch: %h",rsp_tag);
    if (rsp_error) $fatal(1,"unexpected compute error");
    @(negedge clk); rsp_ready=1;
    @(negedge clk); rsp_ready=0;

    send(8'd1, 16'h5678,
         {16'sd4,-16'sd3,16'sd2,-16'sd1}, 64'd0, 40'sd0);
    wait(rsp_valid);
    if (rsp_result !== 40'sd6) $fatal(1,"ReLU expected 6 got %0d",rsp_result);
    if (rsp_tag !== 16'h5678) $fatal(1,"second tag mismatch: %h",rsp_tag);
    @(negedge clk); rsp_ready=1;
    @(negedge clk); rsp_ready=0;

    send(8'hff, 16'h9999, 64'd0, 64'd0, 40'd0);
    wait(illegal_opcode);
    $display("NEXUS chip top integration tests PASS");
    $finish;
  end
endmodule
