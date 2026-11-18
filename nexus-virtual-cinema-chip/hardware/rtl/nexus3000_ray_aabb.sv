// NEXUS-3000 Ray/AABB intersection accelerator v0.3.
// Fixed-point Q16.16 slab test. Inputs are ray origin, reciprocal direction,
// and axis-aligned bounds. Returns the clipped [t_near,t_far] interval.
// This is a building block for BVH traversal, not a complete ray tracer.
module nexus3000_ray_aabb (
  input  logic clk,
  input  logic rst_n,
  input  logic req_valid,
  output logic req_ready,
  input  logic signed [31:0] origin_x, origin_y, origin_z,
  input  logic signed [31:0] invdir_x, invdir_y, invdir_z,
  input  logic signed [31:0] box_min_x, box_min_y, box_min_z,
  input  logic signed [31:0] box_max_x, box_max_y, box_max_z,
  input  logic signed [31:0] t_min,
  input  logic signed [31:0] t_max,
  output logic rsp_valid,
  input  logic rsp_ready,
  output logic hit,
  output logic signed [31:0] t_near,
  output logic signed [31:0] t_far
);
  logic signed [63:0] x0p, x1p, y0p, y1p, z0p, z1p;
  logic signed [31:0] xa, xb, ya, yb, za, zb;
  logic signed [31:0] xnear, xfar, ynear, yfar, znear, zfar;
  logic signed [31:0] near_xy, far_xy, near_all, far_all;
  logic hit_comb;

  always_comb begin
    x0p = ($signed(box_min_x) - $signed(origin_x)) * $signed(invdir_x);
    x1p = ($signed(box_max_x) - $signed(origin_x)) * $signed(invdir_x);
    y0p = ($signed(box_min_y) - $signed(origin_y)) * $signed(invdir_y);
    y1p = ($signed(box_max_y) - $signed(origin_y)) * $signed(invdir_y);
    z0p = ($signed(box_min_z) - $signed(origin_z)) * $signed(invdir_z);
    z1p = ($signed(box_max_z) - $signed(origin_z)) * $signed(invdir_z);

    xa = x0p >>> 16; xb = x1p >>> 16;
    ya = y0p >>> 16; yb = y1p >>> 16;
    za = z0p >>> 16; zb = z1p >>> 16;

    xnear = (xa < xb) ? xa : xb;
    xfar  = (xa > xb) ? xa : xb;
    ynear = (ya < yb) ? ya : yb;
    yfar  = (ya > yb) ? ya : yb;
    znear = (za < zb) ? za : zb;
    zfar  = (za > zb) ? za : zb;

    near_xy = (xnear > ynear) ? xnear : ynear;
    far_xy  = (xfar < yfar) ? xfar : yfar;
    near_all = (near_xy > znear) ? near_xy : znear;
    far_all  = (far_xy < zfar) ? far_xy : zfar;

    if (near_all < t_min) near_all = t_min;
    if (far_all > t_max) far_all = t_max;
    hit_comb = (far_all >= near_all) && (far_all >= t_min) && (near_all <= t_max);
  end

  assign req_ready = !rsp_valid || rsp_ready;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_valid <= 1'b0;
      hit <= 1'b0;
      t_near <= '0;
      t_far <= '0;
    end else if (req_valid && req_ready) begin
      rsp_valid <= 1'b1;
      hit <= hit_comb;
      t_near <= near_all;
      t_far <= far_all;
    end else if (rsp_valid && rsp_ready) begin
      rsp_valid <= 1'b0;
    end
  end
endmodule
