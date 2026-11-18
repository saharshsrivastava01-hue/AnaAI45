// NEXUS-3000 triangle intersection unit v0.5.
// Moller-Trumbore ray/triangle test. Coordinates and t/u/v use signed Q8.8.
// This is a small synthesizable reference block, not a production RT core.
module nexus3000_triangle_intersect (
  input  logic signed [15:0] ro_x, ro_y, ro_z,
  input  logic signed [15:0] rd_x, rd_y, rd_z,
  input  logic signed [15:0] v0_x, v0_y, v0_z,
  input  logic signed [15:0] v1_x, v1_y, v1_z,
  input  logic signed [15:0] v2_x, v2_y, v2_z,
  input  logic signed [15:0] t_min,
  input  logic signed [15:0] t_max,
  output logic hit,
  output logic signed [15:0] t_out,
  output logic signed [15:0] u_out,
  output logic signed [15:0] v_out
);
  function automatic logic signed [47:0] mul16x32(
    input logic signed [15:0] a, input logic signed [31:0] b);
    mul16x32 = a*b;
  endfunction
  function automatic logic signed [31:0] cross_x(
    input logic signed [15:0] ay, az, by, bz);
    cross_x = ay*bz - az*by;
  endfunction
  function automatic logic signed [31:0] cross_y(
    input logic signed [15:0] ax, az, bx, bz);
    cross_y = az*bx - ax*bz;
  endfunction
  function automatic logic signed [31:0] cross_z(
    input logic signed [15:0] ax, ay, bx, by);
    cross_z = ax*by - ay*bx;
  endfunction

  logic signed [15:0] e1x,e1y,e1z,e2x,e2y,e2z,tx,ty,tz;
  logic signed [31:0] px,py,pz,qx,qy,qz;
  logic signed [47:0] det, u_num, v_num, t_num;
  logic signed [47:0] p0,p1,p2;
  logic signed [63:0] t_scaled,u_scaled,v_scaled;

  always_comb begin
    e1x = v1_x-v0_x; e1y = v1_y-v0_y; e1z = v1_z-v0_z;
    e2x = v2_x-v0_x; e2y = v2_y-v0_y; e2z = v2_z-v0_z;
    tx = ro_x-v0_x; ty = ro_y-v0_y; tz = ro_z-v0_z;

    px = cross_x(rd_y,rd_z,e2_y,e2_z);
    py = cross_y(rd_x,rd_z,e2_x,e2_z);
    pz = cross_z(rd_x,rd_y,e2_x,e2_y);
    p0 = mul16x32(e1x,px); p1 = mul16x32(e1y,py); p2 = mul16x32(e1z,pz);
    det = p0+p1+p2;

    u_num = mul16x32(tx,px) + mul16x32(ty,py) + mul16x32(tz,pz);
    qx = cross_x(ty,tz,e1y,e1z);
    qy = cross_y(tx,tz,e1x,e1z);
    qz = cross_z(tx,ty,e1x,e1y);
    v_num = mul16x32(rd_x,qx) + mul16x32(rd_y,qy) + mul16x32(rd_z,qz);
    t_num = mul16x32(e2x,qx) + mul16x32(e2y,qy) + mul16x32(e2z,qz);

    hit = 1'b0;
    t_out = '0; u_out = '0; v_out = '0;
    t_scaled = '0; u_scaled = '0; v_scaled = '0;
    if (det != 0) begin
      if (det > 0) begin
        if ((u_num >= 0) && (v_num >= 0) && ((u_num+v_num) <= det)) begin
          t_scaled = ({{16{t_num[47]}},t_num} <<< 8) / det;
          u_scaled = ({{16{u_num[47]}},u_num} <<< 8) / det;
          v_scaled = ({{16{v_num[47]}},v_num} <<< 8) / det;
          if ((t_scaled >= t_min) && (t_scaled <= t_max) &&
              (t_scaled <= 32767) && (t_scaled >= -32768)) begin
            hit=1'b1; t_out=t_scaled[15:0];
            u_out=u_scaled[15:0]; v_out=v_scaled[15:0];
          end
        end
      end else begin
        if ((u_num <= 0) && (v_num <= 0) && ((u_num+v_num) >= det)) begin
          t_scaled = ({{16{t_num[47]}},t_num} <<< 8) / det;
          u_scaled = ({{16{u_num[47]}},u_num} <<< 8) / det;
          v_scaled = ({{16{v_num[47]}},v_num} <<< 8) / det;
          if ((t_scaled >= t_min) && (t_scaled <= t_max) &&
              (t_scaled <= 32767) && (t_scaled >= -32768)) begin
            hit=1'b1; t_out=t_scaled[15:0];
            u_out=u_scaled[15:0]; v_out=v_scaled[15:0];
          end
        end
      end
    end
  end
endmodule
