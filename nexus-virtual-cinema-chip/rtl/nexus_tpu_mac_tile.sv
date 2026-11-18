// NEXUS-3000 Prototype A: 4-lane signed INT8 MAC tile.
// Synthesizable SystemVerilog starter; not a trillion-core implementation.
module nexus_tpu_mac_tile #(
    parameter int LANES = 4,
    parameter int DATA_W = 8,
    parameter int ACC_W = 32
) (
    input  logic clk,
    input  logic rst_n,
    input  logic in_valid,
    output logic in_ready,
    input  logic signed [DATA_W-1:0] a [LANES],
    input  logic signed [DATA_W-1:0] b [LANES],
    input  logic clear_acc,
    output logic out_valid,
    input  logic out_ready,
    output logic signed [ACC_W-1:0] accum [LANES]
);
    logic signed [2*DATA_W-1:0] product [LANES];
    logic signed [ACC_W-1:0] extended_product [LANES];
    logic valid_q;

    always_comb begin
        in_ready = !valid_q || out_ready;
        for (int i = 0; i < LANES; i++) begin
            product[i] = a[i] * b[i];
            extended_product[i] = {{(ACC_W-2*DATA_W){product[i][2*DATA_W-1]}}, product[i]};
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_q <= 1'b0;
            for (int i = 0; i < LANES; i++) accum[i] <= '0;
        end else if (in_valid && in_ready) begin
            for (int i = 0; i < LANES; i++)
                accum[i] <= clear_acc ? extended_product[i] : accum[i] + extended_product[i];
            valid_q <= 1'b1;
        end else if (out_valid && out_ready) begin
            valid_q <= 1'b0;
        end
    end

    assign out_valid = valid_q;
endmodule
