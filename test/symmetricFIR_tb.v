`timescale 1ns / 1ps

module symmetricFIR_tb();
    parameter COEFF_NUM = 6;
    parameter COEFF_WIDTH = 8;
    parameter DATA_DELAY = 12;
    parameter DATA_WIDTH = 12;
    parameter COEFF_SUM = 196;
    parameter OUTPUT_WIDTH = DATA_WIDTH;
    parameter MAX_SAMPLES = 4096;
    parameter TOLERANCE = 1;

    // GOLDEN_OFFSET: RTL latency in clock cycles = 15
    parameter integer GOLDEN_OFFSET = 15;

    reg clk;
    reg clr;
    reg load;
    reg signed [COEFF_WIDTH-1:0] coeff_value;
    reg signed [DATA_WIDTH-1:0] noisy_signal;

    wire signed [OUTPUT_WIDTH-1:0] filtered_signal;
    wire filtered_valid;

    integer CLK_PERIOD = 10;
    integer fd_coeff;
    integer fd_input;
    integer fd_golden;
    integer fd_log;

    integer sample_count;
    integer golden_value;
    integer rtl_value;
    integer abs_error;
    integer max_error;
    integer total_errors;
    integer compared_samples;
    integer golden_available;

    integer idx;
    integer value;

    reg signed [DATA_WIDTH-1:0] input_samples  [0:MAX_SAMPLES-1];
    reg signed [DATA_WIDTH-1:0] golden_samples [0:MAX_SAMPLES-1];

    symmetricFIR #(
        .COEFF_NUM(COEFF_NUM),
        .COEFF_WIDTH(COEFF_WIDTH),
        .DATA_DELAY(DATA_DELAY),
        .DATA_WIDTH(DATA_WIDTH),
        .COEFF_SUM(COEFF_SUM),
        .OUTPUT_WIDTH(OUTPUT_WIDTH)
    ) DUT (
        .clk(clk),
        .clr(clr),
        .load(load),
        .coeff_value(coeff_value),
        .noisy_signal(noisy_signal),
        .filtered_signal(filtered_signal),
        .filtered_valid(filtered_valid)
    );

    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Read 12-bit hex, convert to signed [-2048..2047]
    function integer read_hex_sample;
        input integer file_handle;
        reg [31:0] hex_value;
        begin
            if ($fscanf(file_handle, "%h", hex_value) != 1)
                read_hex_sample = 32'hffffffff;
            else if (hex_value >= 2048)
                read_hex_sample = hex_value - 4096;
            else
                read_hex_sample = hex_value;
        end
    endfunction

    initial begin
        init_dut();
        preload_files();
        load_coeffs();
        fork
            compare_outputs();
            begin
                stream_input_samples();
                report_results();
            end
        join
    end

    task init_dut;
        begin
            clr = 1;
            load = 0;
            coeff_value = 0;
            noisy_signal = 0;

            sample_count = 0;
            max_error = 0;
            total_errors = 0;
            compared_samples = 0;
            golden_available = 0;

            @(negedge clk);
            clr = 0;
        end
    endtask

    task preload_files;
        begin
            fd_input = $fopen("input_signal.txt", "r");
            if (fd_input == 0)
                $fatal(1, "ERROR: Unable to open input_signal.txt");

            fd_golden = $fopen("filtered_signal.txt", "r");
            if (fd_golden == 0)
                $display("WARNING: filtered_signal.txt not found. Self-check disabled.");
            else
                golden_available = 1;

            sample_count = 0;
            while (sample_count < MAX_SAMPLES) begin
                value = read_hex_sample(fd_input);
                if (value == 32'hffffffff)
                    sample_count = MAX_SAMPLES;
                else begin
                    input_samples[sample_count] = value;
                    if (golden_available)
                        golden_samples[sample_count] = read_hex_sample(fd_golden);
                    sample_count = sample_count + 1;
                end
            end

            $fclose(fd_input);
            if (golden_available)
                $fclose(fd_golden);

            $display("Loaded %0d input samples", sample_count);
        end
    endtask

    task load_coeffs;
        integer k;
        begin
            load = 1;
            fd_coeff = $fopen("coeff_val.txt", "r");
            if (fd_coeff == 0)
                $fatal(1, "ERROR: Unable to open coeff_val.txt");

            for (k = 0; k < COEFF_NUM; k = k + 1) begin
                if ($fscanf(fd_coeff, "%d", coeff_value) != 1)
                    $fatal(1, "ERROR: coeff_val.txt has fewer than %0d coefficients", COEFF_NUM);
                @(negedge clk);
            end

            $fclose(fd_coeff);
            load = 0;

            @(negedge clk);
        end
    endtask

    task stream_input_samples;
        begin
            for (idx = 0; idx < sample_count; idx = idx + 1) begin
                noisy_signal = input_samples[idx];
                @(negedge clk);
            end
            noisy_signal = 0;
        end
    endtask

    task compare_outputs;
        integer golden_index;
        integer out_count;
        begin
            out_count = 0;

            fd_log = $fopen("rtl_output_log.txt", "w");
            if (fd_log == 0)
                $display("WARNING: Unable to create rtl_output_log.txt");

            forever @(posedge clk) begin
                if (filtered_valid && golden_available) begin
                    golden_index = out_count - GOLDEN_OFFSET;

                    if (golden_index >= 0 && golden_index < sample_count) begin
                        rtl_value = filtered_signal;
                        golden_value = golden_samples[golden_index];

                        abs_error = rtl_value - golden_value;
                        if (abs_error < 0) abs_error = -abs_error;

                        if (abs_error > max_error) max_error = abs_error;

                        if (fd_log != 0)
                            $fwrite(fd_log, "%0d %0d %0d\n", golden_index, rtl_value, golden_value);

                        if (abs_error > TOLERANCE) begin
                            total_errors = total_errors + 1;
                            $display("MISMATCH at sample %0d: rtl=%0d golden=%0d err=%0d",
                                     golden_index, rtl_value, golden_value, abs_error);
                        end

                        compared_samples = compared_samples + 1;
                    end

                    out_count = out_count + 1;
                end
            end
        end
    endtask

    task report_results;
        begin
            #(CLK_PERIOD * (sample_count + 100));
            if (fd_log != 0) $fclose(fd_log);

            $display("----------------------------------------");
            $display("Simulation summary");
            $display("Compared samples : %0d", compared_samples);
            $display("Maximum abs error: %0d", max_error);
            $display("Tolerance        : %0d", TOLERANCE);
            $display("Total mismatches : %0d", total_errors);

            if (!golden_available)
                $display("RESULT: MANUAL REVIEW (golden file missing)");
            else if (total_errors == 0)
                $display("RESULT: PASS");
            else
                $display("RESULT: FAIL");

            $display("----------------------------------------");
            $finish;
        end
    endtask
endmodule 