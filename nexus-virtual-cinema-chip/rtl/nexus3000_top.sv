// NEXUS-3000 single-issue virtual cinema command/control fabric.
// Synthesizable SystemVerilog prototype; not a GPU or NPU datapath.
module nexus3000_top (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [2:0]  cmd_opcode,
    input  logic [31:0] cmd_descriptor,
    output logic        rsp_valid,
    output logic [2:0]  rsp_engine,
    output logic [31:0] rsp_descriptor,
    output logic        rsp_error,
    input  logic [6:0]  engine_done,
    input  logic [6:0]  engine_error,
    output logic [6:0]  engine_start,
    output logic [2:0]  engine_select,
    output logic [31:0] engine_descriptor,
    output logic        busy,
    output logic [31:0] accepted_count,
    output logic [31:0] completed_count,
    output logic [31:0] error_count
);
    typedef enum logic [1:0] {IDLE, WAIT_ENGINE, RESPOND} state_t;
    state_t state;
    logic [2:0] active_engine;
    logic [31:0] active_descriptor;
    logic active_error;

    assign cmd_ready = (state == IDLE);
    assign busy = (state != IDLE);
    assign engine_select = active_engine;
    assign engine_descriptor = active_descriptor;

    always_comb begin
        engine_start = 7'b0;
        if ((state == IDLE) && cmd_valid && (cmd_opcode <= 3'd6))
            engine_start[cmd_opcode] = 1'b1;
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            active_engine <= 3'd0;
            active_descriptor <= 32'd0;
            active_error <= 1'b0;
            rsp_valid <= 1'b0;
            rsp_engine <= 3'd0;
            rsp_descriptor <= 32'd0;
            rsp_error <= 1'b0;
            accepted_count <= 32'd0;
            completed_count <= 32'd0;
            error_count <= 32'd0;
        end else begin
            rsp_valid <= 1'b0;
            case (state)
                IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        if (cmd_opcode <= 3'd6) begin
                            active_engine <= cmd_opcode;
                            active_descriptor <= cmd_descriptor;
                            active_error <= 1'b0;
                            accepted_count <= accepted_count + 1'b1;
                            state <= WAIT_ENGINE;
                        end else begin
                            rsp_valid <= 1'b1;
                            rsp_engine <= cmd_opcode;
                            rsp_descriptor <= cmd_descriptor;
                            rsp_error <= 1'b1;
                            error_count <= error_count + 1'b1;
                        end
                    end
                end
                WAIT_ENGINE: begin
                    if (engine_done[active_engine] || engine_error[active_engine]) begin
                        active_error <= engine_error[active_engine];
                        state <= RESPOND;
                    end
                end
                RESPOND: begin
                    rsp_valid <= 1'b1;
                    rsp_engine <= active_engine;
                    rsp_descriptor <= active_descriptor;
                    rsp_error <= active_error;
                    completed_count <= completed_count + 1'b1;
                    if (active_error)
                        error_count <= error_count + 1'b1;
                    state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
