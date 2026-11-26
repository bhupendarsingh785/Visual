// Leaky integrate-and-fire neuron. Fixed-point-free integer reference RTL.
module ai_spiking_neuron #(
    parameter integer STATE_W = 16,
    parameter integer THRESHOLD = 100,
    parameter integer LEAK = 1
) (
    input logic clk,
    input logic rst_n,
    input logic en,
    input logic [STATE_W-1:0] input_current,
    output logic spike,
    output logic [STATE_W-1:0] membrane
);
    logic [STATE_W:0] accumulated;
    always_comb accumulated = {1'b0, membrane} + input_current;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            membrane <= '0;
            spike <= 1'b0;
        end else if (en) begin
            if (accumulated >= THRESHOLD) begin
                spike <= 1'b1;
                membrane <= '0;
            end else begin
                spike <= 1'b0;
                if (accumulated > LEAK) membrane <= accumulated - LEAK;
                else membrane <= '0;
            end
        end else spike <= 1'b0;
    end
endmodule
