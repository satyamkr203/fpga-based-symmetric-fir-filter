# FPGA Symmetric FIR Filter

A hardware implementation of a 12-tap linear-phase symmetric FIR filter in Verilog HDL with fixed-point arithmetic, Python-based golden reference verification, and Xilinx Vivado simulation.

## Overview

This project demonstrates the complete FPGA DSP design flow:

* FIR filter design
* Fixed-point arithmetic implementation
* Verilog RTL development
* Self-checking verification
* Vivado simulation
* FPGA synthesis and implementation analysis

The design exploits coefficient symmetry to reduce the number of multipliers by approximately 50%, improving hardware efficiency while preserving linear-phase filtering characteristics.

## Features

* 12-tap symmetric FIR architecture
* Linear-phase response
* Fixed-point implementation
* 3-stage pipelined datapath
* Self-checking Verilog testbench
* Python golden reference model
* Automatic PASS/FAIL verification
* Vivado simulation support
* Resource utilization analysis
* Timing and power evaluation

## Architecture

### Filter Configuration

| Parameter           | Value         |
| ------------------- | ------------- |
| Filter Type         | Symmetric FIR |
| Number of Taps      | 12            |
| Unique Coefficients | 6             |
| Input Width         | 12-bit Signed |
| Coefficient Width   | 8-bit Signed  |
| Output Width        | 12-bit Signed |
| Pipeline Stages     | 3             |
| Clock Frequency     | 100 MHz       |

### Coefficients

Half-kernel:

[2, 14, 7, 28, 15, 32]

Full symmetric impulse response:

[2, 14, 7, 28, 15, 32, 32, 15, 28, 7, 14, 2]

### Optimization

The architecture uses coefficient symmetry:

h[k] = h[N−1−k]

This reduces multiplier usage from 12 to 6 by pre-adding symmetric input samples before multiplication.

## Project Structure

```text
├── src/
│   └── symmetricFIR.v
├── test/
│   └── symmetricFIR_tb.v
├── docs/
│   ├── waveforms
│   ├── synthesis_reports
│   └── screenshots
├── generate_noisy_signal.py
├── coeff_val.txt
├── input_signal.txt
├── filtered_signal.txt
└── README.md
```

## Verification Flow

1. Python generates noisy test signals.
2. Golden FIR outputs are computed.
3. Test vectors are exported.
4. Verilog testbench loads vectors.
5. RTL outputs are compared against golden outputs.
6. PASS/FAIL results are reported automatically.

## Test Signals

The filter was evaluated using:

* Sine Wave
* Sawtooth Wave
* Square Wave
* Chirp Signal
* Pulse Signal
* Triangular Signal
* Composite Signals

## Tools Used

* Verilog HDL
* Python
* Xilinx Vivado
* XSim Simulator
* FPGA Design Flow

## Results

The RTL implementation matched the Python reference model with zero observed output error during functional verification.

Key evaluations include:

* Behavioral Simulation
* Resource Utilization
* Timing Analysis
* Power Analysis
* Design Rule Check (DRC)
* FPGA Floorplanning

## Future Improvements

* Hardware deployment on FPGA board
* AXI Stream integration
* UART-based coefficient loading
* Runtime coefficient updates
* Comparison with direct-form FIR architectures
* Polyphase and multirate filter extensions

## Author

Satyam Kumar
