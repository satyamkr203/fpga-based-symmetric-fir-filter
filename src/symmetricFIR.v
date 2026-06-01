`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// symmetricFIR: 12-tap symmetric FIR using 6 unique coefficients
//////////////////////////////////////////////////////////////////////////////////

module symmetricFIR #(
    parameter COEFF_NUM    = 6,
    parameter COEFF_WIDTH  = 8,
    parameter DATA_DELAY   = COEFF_NUM * 2,     // 12
    parameter DATA_WIDTH   = 12,
    parameter COEFF_SUM    = 196,
    parameter STAGE1_WIDTH = DATA_WIDTH + 1,
    parameter STAGE2_WIDTH = STAGE1_WIDTH + COEFF_WIDTH + 1,
    parameter ACCUM_WIDTH  = STAGE2_WIDTH + 3,
    parameter OUTPUT_WIDTH = DATA_WIDTH
)(
    input  wire clk,
    input  wire clr,
    input  wire load,
    input  wire signed [COEFF_WIDTH-1:0] coeff_value,
    input  wire signed [DATA_WIDTH-1:0]  noisy_signal,
    output reg  signed [OUTPUT_WIDTH-1:0] filtered_signal,
    output reg  filtered_valid
);

    // Coefficients
    reg signed [COEFF_WIDTH-1:0] coeff_reg [0:COEFF_NUM-1];
    reg [$clog2(COEFF_NUM)-1:0]  coeff_array_index;
    reg coeff_loaded;

    // Delay line (data_reg[0]=newest, data_reg[11]=oldest)
    reg signed [DATA_WIDTH-1:0] data_reg [0:DATA_DELAY-1];

    // Control
    reg data_loaded;
    reg [1:0] data_ready_counter;
    reg [$clog2(DATA_DELAY)-1:0] data_loaded_counter;
    reg pipeline_active;

    // Pipeline regs
    reg signed [STAGE1_WIDTH-1:0] stage1_add_reg [0:COEFF_NUM-1];
    reg signed [STAGE2_WIDTH-1:0] stage2_mul_reg [0:COEFF_NUM-1];

    // Moved out of always block (Verilog compliant)
    reg signed [ACCUM_WIDTH-1:0] sum_next;
    reg signed [ACCUM_WIDTH-1:0] scaled_next;

    // Fill delay line after coeffs are loaded
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            data_loaded_counter <= 0;
            data_loaded <= 1'b0;
        end else if (coeff_loaded) begin
            if (data_loaded_counter == DATA_DELAY-1) begin
                data_loaded <= 1'b1;
            end else begin
                data_loaded_counter <= data_loaded_counter + 1'b1;
                data_loaded <= 1'b0;
            end
        end
    end

    // Delay line shift register
    always @(posedge clk or posedge clr) begin
        if (clr)
            data_reg[0] <= 0;
        else if (coeff_loaded)
            data_reg[0] <= noisy_signal;
    end

    genvar i;
    generate
        for (i = 1; i < DATA_DELAY; i = i + 1) begin : shift_reg
            always @(posedge clk or posedge clr) begin
                if (clr)
                    data_reg[i] <= 0;
                else if (coeff_loaded)
                    data_reg[i] <= data_reg[i-1];
            end
        end
    endgenerate

    // Coefficient load (robust)
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            coeff_array_index <= 0;
            coeff_loaded <= 1'b0;
        end else if (!coeff_loaded) begin
            if (load) begin
                coeff_reg[coeff_array_index] <= coeff_value;

                if (coeff_array_index == COEFF_NUM-1) begin
                    coeff_loaded <= 1'b1;
                    coeff_array_index <= 0;
                end else begin
                    coeff_array_index <= coeff_array_index + 1'b1;
                end
            end
        end
    end

    // Pipeline enable after delay line fill
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            data_ready_counter <= 0;
            pipeline_active <= 1'b0;
        end else if (data_loaded) begin
            pipeline_active <= 1'b1;
            if (data_ready_counter != 2'b10)
                data_ready_counter <= data_ready_counter + 1'b1;
        end
    end

    // FIR: symmetric pre-add + multiply
    genvar j;
    generate
        for (j = 0; j < COEFF_NUM; j = j + 1) begin : fir_pipeline
            always @(posedge clk or posedge clr) begin
                if (clr) begin
                    stage1_add_reg[j] <= 0;
                    stage2_mul_reg[j] <= 0;
                end else if (pipeline_active) begin
                    stage1_add_reg[j] <= data_reg[j] + data_reg[(DATA_DELAY-1) - j];
                    stage2_mul_reg[j] <= stage1_add_reg[j] * coeff_reg[j];
                end
            end
        end
    endgenerate

    // Output stage: sum 6 products, round divide, saturate
    always @(posedge clk or posedge clr) begin
        if (clr) begin
            sum_next <= 0;
            scaled_next <= 0;
            filtered_signal <= 0;
            filtered_valid  <= 1'b0;
        end else if (pipeline_active && data_ready_counter == 2'b10) begin
            // blocking assignments to compute current-cycle values
            sum_next =
                stage2_mul_reg[0] + stage2_mul_reg[1] + stage2_mul_reg[2] +
                stage2_mul_reg[3] + stage2_mul_reg[4] + stage2_mul_reg[5];

            scaled_next = (sum_next + (COEFF_SUM/2)) / COEFF_SUM;

            if (scaled_next > 2047)
                filtered_signal <= 2047;
            else if (scaled_next < -2048)
                filtered_signal <= -2048;
            else
                filtered_signal <= scaled_next[OUTPUT_WIDTH-1:0];

            filtered_valid <= 1'b1;
        end else begin
            filtered_valid <= 1'b0;
        end
    end

endmodule