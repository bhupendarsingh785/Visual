`timescale 1ns/1ps
module tb_visual_ai_chip_cluster;
    localparam TILES=4, LANES=8, ACC=32;
    reg clk=0, rst_n=0;
    reg [TILES-1:0] tile_valid, tile_clear;
    reg [TILES*LANES*8-1:0] tile_a, tile_b;
    wire [TILES-1:0] tile_ready, tile_out_valid;
    wire [TILES*ACC-1:0] tile_accumulators;
    integer i;
    always #5 clk=~clk;

    visual_ai_chip_cluster #(.TILES(TILES),.LANES_PER_TILE(LANES),.ACC_WIDTH(ACC)) dut(
      .clk(clk),.rst_n(rst_n),.tile_valid(tile_valid),.tile_a(tile_a),.tile_b(tile_b),
      .tile_clear(tile_clear),.tile_ready(tile_ready),.tile_out_valid(tile_out_valid),
      .tile_accumulators(tile_accumulators)
    );

    initial begin
      tile_valid=0; tile_clear=0; tile_a=0; tile_b=0;
      repeat(2) @(negedge clk); rst_n=1;
      if (tile_ready !== 4'b1111) $fatal(1,"ready must be asserted");
      // Each tile receives eight 2*3 products => 48.
      for (i=0;i<TILES*LANES;i=i+1) begin
        tile_a[i*8 +: 8]=8'd2;
        tile_b[i*8 +: 8]=8'd3;
      end
      tile_valid=4'b1111;
      @(negedge clk);
      tile_valid=0;
      if (tile_out_valid !== 4'b1111) $fatal(1,"valid pulse missing");
      for (i=0;i<TILES;i=i+1)
        if ($signed(tile_accumulators[i*ACC +: ACC]) !== 32'sd48)
          $fatal(1,"tile %0d dot product mismatch",i);
      // Accumulate a second vector, then clear only tile 1.
      tile_valid=4'b1111; tile_clear=0;
      @(negedge clk); tile_valid=0;
      tile_clear=4'b0010;
      @(negedge clk); tile_clear=0;
      if ($signed(tile_accumulators[0*ACC +: ACC]) !== 32'sd96) $fatal(1,"tile0 accumulation failed");
      if ($signed(tile_accumulators[1*ACC +: ACC]) !== 32'sd0) $fatal(1,"tile1 clear failed");
      if ($signed(tile_accumulators[2*ACC +: ACC]) !== 32'sd96) $fatal(1,"tile2 accumulation failed");
      if ($signed(tile_accumulators[3*ACC +: ACC]) !== 32'sd96) $fatal(1,"tile3 accumulation failed");
      $display("VISUAL multi-tile MAC cluster tests PASS");
      $finish;
    end
endmodule
