// NEXUS-3000 BVH traversal controller v0.4.
// Iterative depth-first traversal controller with a bounded on-chip node stack.
// A separate BVH memory/intersection unit supplies node metadata and hit flags.
// Node indices are opaque addresses into an external BVH node store.
module nexus3000_bvh_traversal #(
  parameter int NODE_W = 16,
  parameter int STACK_DEPTH = 16,
  parameter int PTR_W = $clog2(STACK_DEPTH)
) (
  input  logic clk,
  input  logic rst_n,
  input  logic start_valid,
  output logic start_ready,
  input  logic [NODE_W-1:0] root_node,

  output logic node_req_valid,
  input  logic node_req_ready,
  output logic [NODE_W-1:0] node_req_index,

  input  logic node_rsp_valid,
  output logic node_rsp_ready,
  input  logic node_hit,
  input  logic node_is_leaf,
  input  logic [NODE_W-1:0] left_child,
  input  logic [NODE_W-1:0] right_child,

  output logic leaf_valid,
  input  logic leaf_ready,
  output logic [NODE_W-1:0] leaf_index,

  output logic done,
  output logic stack_overflow
);
  typedef enum logic [1:0] {IDLE, REQUEST_NODE, WAIT_NODE, EMIT_LEAF, FINISHED} state_t;
  state_t state;
  logic [NODE_W-1:0] stack [0:STACK_DEPTH-1];
  logic [PTR_W:0] stack_count;
  logic [NODE_W-1:0] current_node;
  logic [NODE_W-1:0] pending_leaf;
  logic push_children;

  assign start_ready = (state == IDLE) || (state == FINISHED);
  assign node_req_valid = (state == REQUEST_NODE);
  assign node_req_index = current_node;
  assign node_rsp_ready = (state == WAIT_NODE);
  assign leaf_valid = (state == EMIT_LEAF);
  assign leaf_index = pending_leaf;
  assign done = (state == FINISHED);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= IDLE;
      stack_count <= '0;
      current_node <= '0;
      pending_leaf <= '0;
      stack_overflow <= 1'b0;
    end else begin
      case (state)
        IDLE, FINISHED: begin
          if (start_valid && start_ready) begin
            current_node <= root_node;
            stack_count <= '0;
            stack_overflow <= 1'b0;
            state <= REQUEST_NODE;
          end
        end
        REQUEST_NODE: begin
          if (node_req_valid && node_req_ready)
            state <= WAIT_NODE;
        end
        WAIT_NODE: begin
          if (node_rsp_valid && node_rsp_ready) begin
            if (!node_hit) begin
              if (stack_count != 0) begin
                stack_count <= stack_count - 1'b1;
                current_node <= stack[stack_count - 1'b1];
                state <= REQUEST_NODE;
              end else begin
                state <= FINISHED;
              end
            end else if (node_is_leaf) begin
              pending_leaf <= current_node;
              state <= EMIT_LEAF;
            end else if (stack_count + 2 > STACK_DEPTH) begin
              stack_overflow <= 1'b1;
              state <= FINISHED;
            end else begin
              // Push right, visit left first (depth-first order).
              stack[stack_count] <= right_child;
              stack[stack_count + 1'b1] <= left_child;
              stack_count <= stack_count + 2;
              current_node <= left_child;
              state <= REQUEST_NODE;
            end
          end
        end
        EMIT_LEAF: begin
          if (leaf_valid && leaf_ready) begin
            if (stack_count != 0) begin
              stack_count <= stack_count - 1'b1;
              current_node <= stack[stack_count - 1'b1];
              state <= REQUEST_NODE;
            end else begin
              state <= FINISHED;
            end
          end
        end
        default: state <= IDLE;
      endcase
    end
  end
endmodule
