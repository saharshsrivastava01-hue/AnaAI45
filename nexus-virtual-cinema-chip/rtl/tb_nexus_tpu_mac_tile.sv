module tb_nexus_tpu_mac_tile;
    localparam int LANES=4, DATA_W=8, ACC_W=32;
    logic clk=0, rst_n=0, in_valid=0, in_ready, clear_acc=0;
    logic out_valid, out_ready=1;
    logic signed [DATA_W-1:0] a [LANES], b [LANES];
    logic signed [ACC_W-1:0] accum [LANES];

    always #5 clk = ~clk;

    nexus_tpu_mac_tile #(.LANES(LANES), .DATA_W(DATA_W), .ACC_W(ACC_W)) dut (.*);

    initial begin
        for (int i=0;i<LANES;i++) begin a[i]=0; b[i]=0; end
        repeat (2) @(negedge clk);
        rst_n=1;
        @(negedge clk);
        a[0]=3; b[0]=4;
        a[1]=-2; b[1]=5;
        a[2]=7; b[2]=2;
        a[3]=1; b[3]=-9;
        in_valid=1; clear_acc=1;
        @(negedge clk);
        in_valid=0; clear_acc=0;
        if (!out_valid) $fatal(1, "expected out_valid");
        if (accum[0] !== 12 || accum[1] !== -10 ||
            accum[2] !== 14 || accum[3] !== -9)
            $fatal(1, "MAC result mismatch");
        $display("PASS: NEXUS TPU MAC tile basic test");
        $finish;
    end
endmodule
