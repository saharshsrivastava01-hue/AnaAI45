`timescale 1ns/1ps
module tb_nexus3000_bvh_traversal;
  logic clk=0, rst_n=0, start_valid=0, node_req_ready=1;
  logic start_ready, node_req_valid, node_rsp_valid=0, node_rsp_ready;
  logic [15:0] root_node=1, node_req_index, left_child=0, right_child=0;
  logic node_hit=1, node_is_leaf=0;
  logic leaf_valid, leaf_ready=1, done, stack_overflow;
  logic [15:0] leaf_index;
  always #5 clk=~clk;
  nexus3000_bvh_traversal dut(.*);

  task automatic respond(input logic hit, input logic leaf,
                         input logic [15:0] left, input logic [15:0] right);
    begin
      wait(node_req_valid);
      @(negedge clk);
      node_rsp_valid=1; node_hit=hit; node_is_leaf=leaf;
      left_child=left; right_child=right;
      @(negedge clk); node_rsp_valid=0;
    end
  endtask

  initial begin
    repeat(2) @(negedge clk); rst_n=1;
    @(negedge clk); start_valid=1;
    @(negedge clk); start_valid=0;

    // Root internal: visit left leaf 2, then deferred right leaf 3.
    respond(1,0,16'd2,16'd3);
    wait(leaf_valid);
    if (leaf_index !== 16'd2) $fatal(1,"expected first leaf 2");
    @(negedge clk);
    respond(1,1,0,0);
    wait(leaf_valid);
    if (leaf_index !== 16'd3) $fatal(1,"expected second leaf 3");
    @(negedge clk);
    wait(done);
    if (stack_overflow) $fatal(1,"unexpected stack overflow");
    $display("NEXUS BVH traversal tests PASS");
    $finish;
  end
endmodule
