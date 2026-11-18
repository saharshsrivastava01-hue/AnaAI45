`timescale 1ns/1ps
module tb_nexus3000_triangle_intersect;
  logic signed [15:0] ro_x,ro_y,ro_z,rd_x,rd_y,rd_z;
  logic signed [15:0] v0_x,v0_y,v0_z,v1_x,v1_y,v1_z,v2_x,v2_y,v2_z;
  logic signed [15:0] t_min,t_max,t_out,u_out,v_out;
  logic hit;
  nexus3000_triangle_intersect dut(.*);
  initial begin
    // Ray through the centre of a unit right triangle at z=1.
    ro_x=16'sd64; ro_y=16'sd64; ro_z=16'sd512;
    rd_x=0; rd_y=0; rd_z=-16'sd256;
    v0_x=0; v0_y=0; v0_z=16'sd256;
    v1_x=16'sd256; v1_y=0; v1_z=16'sd256;
    v2_x=0; v2_y=16'sd256; v2_z=16'sd256;
    t_min=1; t_max=16'sd2048;
    #1;
    if (!hit) $fatal(1,"expected triangle hit");
    if (t_out < 16'sd250 || t_out > 16'sd262) $fatal(1,"unexpected t");
    if (u_out < 16'sd60 || u_out > 16'sd68) $fatal(1,"unexpected u");
    if (v_out < 16'sd60 || v_out > 16'sd68) $fatal(1,"unexpected v");

    // Parallel ray must miss.
    rd_z=0; rd_x=16'sd256; #1;
    if (hit) $fatal(1,"parallel ray should miss");
    $display("NEXUS triangle intersection tests PASS");
    $finish;
  end
endmodule
