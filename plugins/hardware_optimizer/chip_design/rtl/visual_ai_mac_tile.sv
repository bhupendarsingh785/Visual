// VISUAL AI MAC tile - synthesizable starter RTL.
// This is a digital design prototype, not a fabricated chip.
// Signed INT8 multiply-accumulate lanes with a simple ready/valid interface.
module visual_ai_mac_tile #(
    parameter integer LANES = 8,
    parameter integer ACC_WIDTH = 32
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         in_valid,
    output wire                         in_ready,
    input  wire signed [LANES*8-1:0]    a_packed,
    input  wire signed [LANES*8-1:0]    b_packed,
    input  wire                         clear_acc,
    output reg                          out_valid,
    output reg signed [ACC_WIDTH-1:0]   accumulator
);
    reg signed [ACC_WIDTH-1:0] sum_next;
    integer i;
    reg signed [7:0] a_lane;
    reg signed [7:0] b_lane;
    reg signed [15:0] product;

    assign in_ready = 1'b1;

    always @* begin
        sum_next = accumulator;
        a_lane = 0;
        b_lane = 0;
        product = 0;
        for (i = 0; i < LANES; i = i + 1) begin
            a_lane = a_packed[i*8 +: 8];
            b_lane = b_packed[i*8 +: 8];
            product = a_lane * b_lane;
            sum_next = sum_next + {{(ACC_WIDTH-16){product[15]}}, product};
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            accumulator <= 0;
            out_valid <= 0;
        end else begin
            out_valid <= in_valid;
            if (clear_acc)
                accumulator <= 0;
            else if (in_valid && in_ready)
                accumulator <= sum_next;
        end
    end
endmodule
