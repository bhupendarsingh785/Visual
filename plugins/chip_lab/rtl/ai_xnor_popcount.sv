// Binary neural-network primitive: XNOR followed by population count.
module ai_xnor_popcount #(
    parameter integer WIDTH = 32,
    parameter integer COUNT_W = $clog2(WIDTH + 1)
) (
    input logic [WIDTH-1:0] activation,
    input logic [WIDTH-1:0] weight,
    output logic [COUNT_W-1:0] matches
);
    integer i;
    always_comb begin
        matches = '0;
        for (i = 0; i < WIDTH; i = i + 1)
            matches = matches + (activation[i] ~^ weight[i]);
    end
endmodule
