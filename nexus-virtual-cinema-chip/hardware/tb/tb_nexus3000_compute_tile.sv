`timescale 1ns/1ps
module tb_nexus3000_compute_tile;
  logic clk=0, rst_n=0, req_valid=0, rsp_ready=0;
  logic req_ready, rsp_valid, error;
  logic [1:0] opcode;
  logic signed [63:0] vec_a, vec_b;
  logic signed [39:0] acc_in, result;
  always #5 clk=~clk;
  nexus3000_compute_tile dut(.*);
  task automatic issue(input logic [1:0] op, input logic signed [63:0] a,
                       input logic signed [63:0] b, input logic signed [39:0] acc);
    begin
      @(negedge clk); opcode=op; vec_a=a; vec_b=b; acc_in=acc; req_valid=1;
      do @(posedge clk); while (!req_ready);
      @(negedge clk); req_valid=0;
      wait(rsp_valid);
    end
  endtask
  initial begin
    opcode=0; vec_a=0; vec_b=0; acc_in=0;
    repeat(2) @(negedge clk); rst_n=1;
    issue(2'b00, {16'sd4,16'sd3,16'sd2,16'sd1},
                    {16'sd8,16'sd7,16'sd6,16'sd5}, 40'sd10);
    if (result !== 40'sd80) $fatal(1,"MAC expected 80 got %0d",result);
    @(negedge clk); rsp_ready=1; @(negedge clk); rsp_ready=0;
    issue(2'b01, {16'sd4,-16'sd3,16'sd2,-16'sd1}, 64'd0, 40'sd0);
    if (result !== 40'sd6) $fatal(1,"ReLU sum expected 6 got %0d",result);
    $display("NEXUS compute tile tests PASS");
    $finish;
  end
endmodule
