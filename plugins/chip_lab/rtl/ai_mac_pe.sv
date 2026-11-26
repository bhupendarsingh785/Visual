// VISUAL Chip Lab: synthesizable signed multiply-accumulate processing element.
module ai_mac_pe #(
    parameter integer DATA_W = 8,
    parameter integer ACC_W = 32
) (
    input  logic clk,
    input  logic rst_n,
    input  logic en,
    input  logic clear_acc,
    input  logic signed [DATA_W-1:0] a_in,
    input  logic signed [DATA_W-1:0] b_in,
    output logic signed [DATA_W-1:0] a_out,
    output logic signed [DATA_W-1:0] b_out,
    output logic signed [ACC_W-1:0] acc
);
    logic signed [2*DATA_W-1:0] product;
    assign product = a_in * b_in;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_out <= '0;
            b_out <= '0;
            acc   <= '0;
        end else if (en) begin
            a_out <= a_in;
            b_out <= b_in;
            if (clear_acc) acc <= {{(ACC_W){1'b0}}};
            else acc <= acc + {{(ACC_W-2*DATA_W){product[2*DATA_W-1]}}, product};
        end
    end
endmodule
