// Four-lane signed INT16 dot-product / matrix-tile primitive.
module nexus3000_tensor_dot #(
  parameter int LANES=4, DATA_W=16, ACC_W=40
)(
  input logic clk, input logic rst_n,
  input logic in_valid, output logic in_ready,
  input logic signed [LANES*DATA_W-1:0] a,
  input logic signed [LANES*DATA_W-1:0] b,
  output logic out_valid, input logic out_ready,
  output logic signed [ACC_W-1:0] dot
);
  logic signed [ACC_W-1:0] sum_comb;
  integer k;
  logic signed [DATA_W-1:0] av,bv;
  always_comb begin
    sum_comb='0;
    for(k=0;k<LANES;k=k+1) begin
      av=$signed(a[k*DATA_W +: DATA_W]);
      bv=$signed(b[k*DATA_W +: DATA_W]);
      sum_comb=sum_comb+(av*bv);
    end
  end
  assign in_ready=!out_valid || out_ready;
  always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin dot<='0; out_valid<=1'b0; end
    else begin
      if(in_valid && in_ready) begin dot<=sum_comb; out_valid<=1'b1; end
      else if(out_valid && out_ready) out_valid<=1'b0;
    end
  end
endmodule
