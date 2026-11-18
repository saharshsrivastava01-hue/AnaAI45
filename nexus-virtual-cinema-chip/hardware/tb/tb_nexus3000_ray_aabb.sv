`timescale 1ns/1ps
module tb_nexus3000_ray_aabb;
  logic clk=0, rst_n=0, req_valid=0, rsp_ready=0;
  logic req_ready, rsp_valid, hit;
  logic signed [31:0] ox=0, oy=0, oz=0;
  logic signed [31:0] ix=32'sh00010000, iy=32'sh00010000, iz=32'sh00010000;
  logic signed [31:0] minx, miny, minz, maxx, maxy, maxz;
  logic signed [31:0] tmin=0, tmax=32'sh00640000, tnear, tfar;
  always #5 clk=~clk;

  nexus3000_ray_aabb dut(
    .clk(clk), .rst_n(rst_n), .req_valid(req_valid), .req_ready(req_ready),
    .origin_x(ox), .origin_y(oy), .origin_z(oz),
    .invdir_x(ix), .invdir_y(iy), .invdir_z(iz),
    .box_min_x(minx), .box_min_y(miny), .box_min_z(minz),
    .box_max_x(maxx), .box_max_y(maxy), .box_max_z(maxz),
    .t_min(tmin), .t_max(tmax), .rsp_valid(rsp_valid),
    .rsp_ready(rsp_ready), .hit(hit), .t_near(tnear), .t_far(tfar)
  );

  task automatic request;
    begin
      @(negedge clk); req_valid=1;
      do @(posedge clk); while (!req_ready);
      @(negedge clk); req_valid=0;
      wait(rsp_valid);
    end
  endtask

  initial begin
    minx=32'sh00020000; maxx=32'sh00040000;
    miny=-32'sh00010000; maxy=32'sh00010000;
    minz=-32'sh00010000; maxz=32'sh00010000;
    repeat(2) @(negedge clk); rst_n=1;
    request();
    if (!hit || tnear !== 32'sh00020000 || tfar !== 32'sh00040000)
      $fatal(1,"expected hit [2,4], got hit=%b near=%h far=%h",hit,tnear,tfar);
    @(negedge clk); rsp_ready=1; @(negedge clk); rsp_ready=0;

    miny=32'sh00020000; maxy=32'sh00040000;
    request();
    if (hit) $fatal(1,"expected miss for disjoint slab intervals");
    $display("NEXUS ray AABB tests PASS");
    $finish;
  end
endmodule
