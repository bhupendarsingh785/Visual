`timescale 1ns/1ps
module tb_visual_ai_compute_tile;
    logic clk=0, rst_n=0;
    logic [1:0] simd_op;
    logic [63:0] simd_a, simd_b, simd_y;
    logic [31:0] bnn_activation, bnn_weight;
    logic [5:0] bnn_matches;
    logic neuron_en;
    logic [15:0] neuron_current, neuron_membrane;
    logic neuron_spike;

    always #5 clk = ~clk;

    visual_ai_compute_tile dut (
        .clk(clk), .rst_n(rst_n),
        .simd_op(simd_op), .simd_a(simd_a), .simd_b(simd_b), .simd_y(simd_y),
        .bnn_activation(bnn_activation), .bnn_weight(bnn_weight), .bnn_matches(bnn_matches),
        .neuron_en(neuron_en), .neuron_current(neuron_current),
        .neuron_spike(neuron_spike), .neuron_membrane(neuron_membrane)
    );

    initial begin
        simd_op=0; simd_a={16'd4,16'd3,16'd2,16'd1}; simd_b={16'd40,16'd30,16'd20,16'd10};
        bnn_activation=32'hffff_0000; bnn_weight=32'hffff_00ff;
        neuron_en=0; neuron_current=0;
        #2; rst_n=1;
        #1;
        if (simd_y !== {16'd44,16'd33,16'd22,16'd11}) $fatal(1,"SIMD add failed");
        if (bnn_matches !== 6'd24) $fatal(1,"XNOR/popcount failed: %0d", bnn_matches);
        simd_op=2'b10; #1;
        if (simd_y !== {16'd160,16'd90,16'd40,16'd10}) $fatal(1,"SIMD multiply failed");
        @(negedge clk); neuron_en=1; neuron_current=16'd60;
        @(posedge clk); #1;
        if (neuron_spike !== 1'b0 || neuron_membrane !== 16'd59)
            $fatal(1,"spiking neuron integration/leak step failed");
        @(negedge clk); neuron_current=16'd50;
        @(posedge clk); #1;
        if (neuron_spike !== 1'b1) $fatal(1,"spiking neuron threshold failed");
        if (neuron_membrane !== 16'd0) $fatal(1,"neuron did not reset membrane");
        $display("VISUAL AI Chip Lab smoke tests PASS");
        $finish;
    end
endmodule
