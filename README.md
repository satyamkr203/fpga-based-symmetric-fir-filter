# Design and Verification of a Fixed-Point Symmetric FIR Filter for FPGA-Based Digital Signal Processing

M.Tech thesis-oriented project: Python golden reference, Verilog RTL, Vivado simulation, and self-checking verification.

---

## Project Goal

Implement a **12-tap linear-phase symmetric FIR low-pass filter** with:

1. Python reference model and test-vector generation
2. Parameterized Verilog RTL exploiting coefficient symmetry
3. Fixed-point scaling (`divide by COEFF_SUM = 196`)
4. Self-checking Vivado testbench against golden output
5. Documentation and plots suitable for dissertation submission

---

## Directory Structure

```
symmetric_FIR_Filter/
├── README.md                      ← This file
├── requirements.txt
├── generate_noisy_signal.py       ← Golden reference + vector export
├── coeff_val.txt                  ← 6 unique FIR coefficients (decimal)
├── input_signal.txt               ← Noisy input (12-bit hex)
├── filtered_signal.txt            ← Golden output (12-bit hex)
├── sim_config.txt                 ← Simulation metadata
├── src/
│   └── symmetricFIR.v             ← RTL design
├── test/
│   └── symmetricFIR_tb.v          ← Self-checking testbench
├── docs/
│   ├── MTECH_THESIS_BLUEPRINT.md  ← Full thesis guide
│   ├── time_domain_signals.png
│   └── frequency_response.png
└── symmetric_FIR_Filter.xpr       ← Vivado project
```

---

## End-to-End Flow

```
Configure signal → Python generates vectors → Testbench loads files
       → RTL symmetric FIR → Compare with golden → PASS/FAIL report
```

### Filter definition

| Parameter | Value |
|-----------|-------|
| Unique coefficients | `[2, 14, 7, 28, 15, 32]` |
| Full 12-tap impulse response | `[2,14,7,28,15,32,32,15,28,7,14,2]` |
| COEFF_SUM | 196 |
| Input width | 12-bit signed |
| Coefficient width | 8-bit signed |
| Output scaling | `(accum + 98) / 196` with saturation |

---

## Quick Start

### 1. Python environment

```bash
cd symmetric_FIR_Filter
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate test vectors

Interactive:

```bash
python generate_noisy_signal.py --interactive
```

Non-interactive (recommended for reproducible thesis results):

```bash
python generate_noisy_signal.py \
  --sample-rate 1000 \
  --signal-freq 10 \
  --noise 0.2 \
  --num-samples 1000 \
  --signal-type sine \
  --output-dir . \
  --docs-dir docs
```

Outputs: `coeff_val.txt`, `input_signal.txt`, `filtered_signal.txt`, `sim_config.txt`, plots in `docs/`.

### 3. Vivado simulation

1. Open `symmetric_FIR_Filter.xpr`
2. Ensure sources point to `src/symmetricFIR.v` and `test/symmetricFIR_tb.v`
3. Copy vector files into the simulation working directory (`xsim/`) if needed
4. Run **Behavioral Simulation**
5. Check console for `RESULT: PASS` or `RESULT: FAIL`
6. Inspect `rtl_output_log.txt` for per-sample comparison

---

## What Changed (Thesis-Ready Improvements)

| Item | Before | After |
|------|--------|-------|
| Python model | 6-tap float convolution | 12-tap symmetric integer model |
| Coefficient scaling | Mismatch with RTL | Shared `COEFF_SUM=196` |
| Sample rate | Ignored | Used in time axis |
| Testbench | Waveform only | Self-checking PASS/FAIL |
| RTL output | Wide unscaled sum | 12-bit scaled + `filtered_valid` |
| Documentation | None in repo | README + thesis blueprint |

---

## M.Tech Thesis Deliverables Checklist

Use `docs/MTECH_THESIS_BLUEPRINT.md` as your master plan. Minimum submission set:

- [ ] Dissertation PDF (80–120 pages typical for M.Tech)
- [ ] RTL + testbench source code
- [ ] Python reference scripts
- [ ] Simulation PASS log + waveform screenshots
- [ ] Synthesis report (LUT/FF/DSP, Fmax)
- [ ] Frequency response and time-domain plots
- [ ] Error analysis table (max error, RMSE, SNR improvement)

---

## Known Next Steps for Full M.Tech Submission

1. Run Vivado **Synthesis + Implementation** on target FPGA (Artix-7 / Zynq)
2. Add resource utilization and timing tables to thesis
3. Compare symmetric FIR vs direct-form FIR (area/latency trade-off)
4. Optional: FPGA top with BRAM ROM + UART streaming interface

See `docs/MTECH_THESIS_BLUEPRINT.md` for the long-term plan.

**Thesis deadline package (start here):**
- `SUBMISSION_CHECKLIST.md` — 10-day sprint to 3 June
- `thesis/00_THESIS_MASTER.md` — copy-paste chapter drafts
- `docs/viva/VIVA_QA.md` — viva answers
- `docs/README.md` — where to put screenshots

---

## Viva Summary (30 seconds)

> Python generates deterministic test vectors using a 12-tap symmetric integer FIR model. Verilog RTL exploits coefficient symmetry to reduce multipliers, applies fixed-point scaling by 196, and is verified in Vivado with an automated golden-reference testbench. Future work includes FPGA synthesis and resource-optimized comparison with direct-form architectures.
