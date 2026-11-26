// Four-lane signed SIMD arithmetic unit. One operation is broadcast to all lanes.
module ai_simd_vector #(
    parameter integer LANES = 4,
    parameter integer DATA_W = 16
) (
    input logic [1:0] op, // 00 add, 01 subtract, 10 multiply-low
    input logic [LANES*DATA_W-1:0] a,
    input logic [LANES*DATA_W-1:0] b,
    output logic [LANES*DATA_W-1:0] y
);
    integer i;
    logic signed [DATA_W-1:0] av, bv;
    logic signed [2*DATA_W-1:0] product;
    always_comb begin
        y = '0;
        av = '0;
        bv = '0;
        product = '0;
        for (i = 0; i < LANES; i = i + 1) begin
            av = $signed(a[i*DATA_W +: DATA_W]);
            bv = $signed(b[i*DATA_W +: DATA_W]);
            product = av * bv;
            case (op)
                2'b00: y[i*DATA_W +: DATA_W] = av + bv;
                2'b01: y[i*DATA_W +: DATA_W] = av - bv;
                2'b10: y[i*DATA_W +: DATA_W] = product[DATA_W-1:0];
                default: y[i*DATA_W +: DATA_W] = '0;
            endcase
        end
    end
endmodule
