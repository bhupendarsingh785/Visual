// VISUAL multi-tile AI compute cluster - FPGA/ASIC exploration top.
// Four independent INT8 MAC tiles operate in parallel.
// A host CPU/GPU/DPU communicates through this simple prototype interface.
module visual_ai_chip_cluster #(
    parameter integer TILES = 4,
    parameter integer LANES_PER_TILE = 8,
    parameter integer ACC_WIDTH = 32
) (
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire [TILES-1:0]                  tile_valid,
    input  wire [TILES*LANES_PER_TILE*8-1:0] tile_a,
    input  wire [TILES*LANES_PER_TILE*8-1:0] tile_b,
    input  wire [TILES-1:0]                  tile_clear,
    output wire [TILES-1:0]                  tile_ready,
    output wire [TILES-1:0]                  tile_out_valid,
    output wire [TILES*ACC_WIDTH-1:0]       tile_accumulators
);
    genvar t;
    generate
        for (t = 0; t < TILES; t = t + 1) begin : gen_tiles
            visual_ai_mac_tile #(
                .LANES(LANES_PER_TILE),
                .ACC_WIDTH(ACC_WIDTH)
            ) tile (
                .clk(clk),
                .rst_n(rst_n),
                .in_valid(tile_valid[t]),
                .in_ready(tile_ready[t]),
                .a_packed(tile_a[t*LANES_PER_TILE*8 +: LANES_PER_TILE*8]),
                .b_packed(tile_b[t*LANES_PER_TILE*8 +: LANES_PER_TILE*8]),
                .clear_acc(tile_clear[t]),
                .out_valid(tile_out_valid[t]),
                .accumulator(tile_accumulators[t*ACC_WIDTH +: ACC_WIDTH])
            );
        end
    endgenerate
endmodule
