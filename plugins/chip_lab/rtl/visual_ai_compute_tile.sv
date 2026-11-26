// Small integration tile exposing independent SIMD, BNN and spiking blocks.
// Systolic MAC PEs are instantiated separately as an array by a system integrator.
module visual_ai_compute_tile (
    input logic clk,
    input logic rst_n,
    input logic [1:0] simd_op,
    input logic [63:0] simd_a,
    input logic [63:0] simd_b,
    output logic [63:0] simd_y,
    input logic [31:0] bnn_activation,
    input logic [31:0] bnn_weight,
    output logic [5:0] bnn_matches,
    input logic neuron_en,
    input logic [15:0] neuron_current,
    output logic neuron_spike,
    output logic [15:0] neuron_membrane
);
    ai_simd_vector #(.LANES(4), .DATA_W(16)) simd (
        .op(simd_op), .a(simd_a), .b(simd_b), .y(simd_y)
    );
    ai_xnor_popcount #(.WIDTH(32), .COUNT_W(6)) bnn (
        .activation(bnn_activation), .weight(bnn_weight), .matches(bnn_matches)
    );
    ai_spiking_neuron #(.STATE_W(16), .THRESHOLD(100), .LEAK(1)) neuron (
        .clk(clk), .rst_n(rst_n), .en(neuron_en),
        .input_current(neuron_current), .spike(neuron_spike), .membrane(neuron_membrane)
    );
endmodule
