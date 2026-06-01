"""
Symmetric FIR reference model and test-vector generator.

The RTL implements a 12-tap linear-phase symmetric FIR built from 6 unique
coefficients. This script generates the golden reference using the same
integer arithmetic (convolve + divide by COEFF_SUM) that the hardware applies.

CRITICAL: The golden output must account for the RTL's pipeline latency.
Python generates causal convolution output, which matches RTL with proper indexing.
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np

# 6 unique half-kernel taps (symmetric 12-tap filter)
COEFF_HALF = np.array([2, 14, 7, 28, 15, 32], dtype=np.int32)
COEFF_FULL = np.concatenate([COEFF_HALF, COEFF_HALF[::-1]])
COEFF_SUM = int(np.sum(COEFF_FULL))  # 196
DATA_SCALE = 2000

# RTL PIPELINE LATENCY: Must match testbench GOLDEN_OFFSET
# = DATA_DELAY (12 samples to fill shift register) + PIPELINE_STAGES (3) = 15
GOLDEN_OFFSET = 15


def generate_triangle_wave(t, freq):
    period = 1.0 / freq
    return 2 * np.abs(2 * (t / period - np.floor(t / period + 0.5))) - 1


def generate_sawtooth_wave(t, freq):
    return 2 * (t * freq - np.floor(0.5 + t * freq))


def generate_pulse_wave(t, freq, duty_cycle=0.3):
    return np.where((t * freq) % 1.0 < duty_cycle, 1.0, -1.0)


def generate_chirp_signal(t, f0=1, f1=20):
    return np.sin(2 * np.pi * (f0 * t + ((f1 - f0) / 2) * t**2))


def build_time_vector(num_samples, sample_rate):
    duration = num_samples / sample_rate
    return np.linspace(0, duration, num_samples, endpoint=False)


def generate_clean_signal(t, freq, signal_type):
    signal_type = signal_type.lower()
    if signal_type == "sine":
        return np.sin(2 * np.pi * freq * t)
    if signal_type == "square":
        return np.sign(np.sin(2 * np.pi * freq * t))
    if signal_type == "cos":
        return np.cos(2 * np.pi * freq * t)
    if signal_type == "triangle":
        return generate_triangle_wave(t, freq)
    if signal_type == "sawtooth":
        return generate_sawtooth_wave(t, freq)
    if signal_type == "pulse":
        return generate_pulse_wave(t, freq)
    if signal_type == "chirp":
        return generate_chirp_signal(t)
    raise ValueError(
        "Unsupported signal type. Choose sine, square, cos, triangle, sawtooth, pulse, or chirp."
    )


def generate_noisy_signal(num_samples, sample_rate, freq, noise_amplitude, signal_type, seed=42):
    """Generate clean signal, add AWGN, scale to 12-bit range."""
    rng = np.random.default_rng(seed)
    t = build_time_vector(num_samples, sample_rate)
    clean_signal = generate_clean_signal(t, freq, signal_type)
    noise = rng.normal(0, noise_amplitude, num_samples)
    noisy_signal = clean_signal + noise
    scaled_signal = np.clip(
        np.round(noisy_signal * DATA_SCALE).astype(np.int32), -2048, 2047
    )
    return scaled_signal, clean_signal, t


def apply_symmetric_fir_integer(signal):
    """
    Causal 12-tap symmetric FIR matching RTL sample-by-sample timing.
    
    Computes: y[i] = sum(h[k] * x[i-k] for k=0..11 if i-k >= 0)
    Then scales by COEFF_SUM and rounds.
    
    This is the EXACT same computation as the RTL will perform,
    but without pipeline latency modeling (latency handled by testbench offset).
    """
    n = len(signal)
    out = np.zeros(n, dtype=np.int64)
    
    for i in range(n):
        acc = 0
        for k in range(len(COEFF_FULL)):
            idx = i - k
            if idx >= 0:
                acc += int(signal[idx]) * int(COEFF_FULL[k])
        
        # Scale by COEFF_SUM with rounding (same as RTL)
        out[i] = (acc + COEFF_SUM // 2) // COEFF_SUM
    
    return np.clip(out, -2048, 2047).astype(np.int32)


def save_decimal_file(values, filename):
    """Save values as decimal, one per line."""
    with open(filename, "w", encoding="utf-8") as handle:
        for value in values:
            handle.write(f"{int(value)}\n")


def save_hex_file(signal, filename, bit_width=12):
    """Save values as 12-bit hex (two's complement), one per line."""
    mask = (1 << bit_width) - 1
    hex_digits = bit_width // 4
    with open(filename, "w", encoding="utf-8") as handle:
        for value in signal:
            value = int(value)
            if value < 0:
                value = (1 << bit_width) + value
            handle.write(f"{value & mask:0{hex_digits}x}\n")


def save_metadata(filename, **kwargs):
    """Save simulation metadata."""
    with open(filename, "w", encoding="utf-8") as handle:
        for key, value in kwargs.items():
            handle.write(f"{key}={value}\n")


def plot_signals(time, clean_signal, noisy_signal, filtered_signal, signal_type, output_dir):
    """Create 3-panel time-domain plot."""
    os.makedirs(output_dir, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(time, clean_signal, label=f"Clean {signal_type}")
    axes[0].set_title(f"Clean {signal_type} Signal")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(time, noisy_signal / DATA_SCALE, label=f"Noisy {signal_type}", alpha=0.8)
    axes[1].set_title(f"Noisy {signal_type} Signal (AWGN)")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(time, filtered_signal / DATA_SCALE, label=f"Filtered {signal_type}", alpha=0.8)
    axes[2].set_title("Filtered Signal (12-tap symmetric FIR, integer model)")
    axes[2].set_xlabel("Time (s)")
    axes[2].grid(True)
    axes[2].legend()

    fig.tight_layout()
    time_plot = os.path.join(output_dir, f"time_domain_{signal_type}.png")
    fig.savefig(time_plot, dpi=150)
    plt.close(fig)
    return time_plot


def plot_frequency_response(output_dir):
    """Plot magnitude response of the FIR filter."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Frequency response via DFT of normalized impulse response
    impulse = np.zeros(512)
    impulse[: len(COEFF_FULL)] = COEFF_FULL / COEFF_SUM
    response = np.fft.rfft(impulse, n=512)
    freq = np.fft.rfftfreq(512, d=1.0)

    fig, ax = plt.subplots(figsize=(10, 4))
    magnitude_db = 20 * np.log10(np.maximum(np.abs(response), 1e-12))
    ax.plot(freq, magnitude_db)
    ax.set_title("Magnitude Response of Symmetric Low-Pass FIR (12-tap)")
    ax.set_xlabel("Normalized Frequency (cycles/sample)")
    ax.set_ylabel("Magnitude (dB)")
    ax.grid(True)
    ax.axvline(x=0.1, color='r', linestyle='--', alpha=0.5, label='~0.1 normalized')
    ax.legend()
    fig.tight_layout()
    freq_plot = os.path.join(output_dir, "frequency_response.png")
    fig.savefig(freq_plot, dpi=150)
    plt.close(fig)
    return freq_plot


def export_vectors(output_dir, noisy_signal, filtered_signal):
    """Export test vectors in formats readable by Verilog testbench."""
    os.makedirs(output_dir, exist_ok=True)
    
    save_decimal_file(COEFF_HALF, os.path.join(output_dir, "coeff_val.txt"))
    save_hex_file(noisy_signal, os.path.join(output_dir, "input_signal.txt"))
    save_hex_file(filtered_signal, os.path.join(output_dir, "filtered_signal.txt"))
    
    save_metadata(
        os.path.join(output_dir, "sim_config.txt"),
        COEFF_SUM=COEFF_SUM,
        DATA_DELAY=len(COEFF_FULL),
        COEFF_NUM=len(COEFF_HALF),
        DATA_WIDTH=12,
        COEFF_WIDTH=8,
        PIPELINE_LATENCY=3,
        SAMPLE_LATENCY=GOLDEN_OFFSET,
        DATA_SCALE=DATA_SCALE,
        GOLDEN_OFFSET=GOLDEN_OFFSET,
    )


def get_user_input():
    """Prompt user for signal parameters."""
    print("\nConfigure test signal parameters:")
    print("---------------------------------")
    sample_rate = int(input("Sample rate (Hz) [default=1000]: ") or 1000)
    signal_freq = float(input("Signal frequency (Hz) [default=10]: ") or 10)
    noise_amplitude = float(input("Noise amplitude (0.0-1.0) [default=0.2]: ") or 0.2)
    num_samples = int(input("Number of samples [default=1000]: ") or 1000)
    print("\nAvailable signal types: sine, square, cos, triangle, sawtooth, pulse, chirp")
    signal_type = input("Signal type [default=sine]: ").lower() or "sine"
    return sample_rate, signal_freq, noise_amplitude, num_samples, signal_type


def run_generation(
    sample_rate=1000,
    signal_freq=10,
    noise_amplitude=0.2,
    num_samples=1000,
    signal_type="sine",
    output_dir=".",
    docs_dir="docs",
    seed=42,
    show_plot=False,
):
    """Generate test vectors and plots."""
    noisy_signal, clean_signal, time = generate_noisy_signal(
        num_samples=num_samples,
        sample_rate=sample_rate,
        freq=signal_freq,
        noise_amplitude=noise_amplitude,
        signal_type=signal_type,
        seed=seed,
    )
    filtered_signal = apply_symmetric_fir_integer(noisy_signal)

    export_vectors(output_dir, noisy_signal, filtered_signal)
    time_plot = plot_signals(time, clean_signal, noisy_signal, filtered_signal, signal_type, docs_dir)
    freq_plot = plot_frequency_response(docs_dir)

    print("\n" + "="*60)
    print("Generated files:")
    print("="*60)
    print(f"  {os.path.join(output_dir, 'coeff_val.txt')}")
    print(f"  {os.path.join(output_dir, 'input_signal.txt')}")
    print(f"  {os.path.join(output_dir, 'filtered_signal.txt')}")
    print(f"  {os.path.join(output_dir, 'sim_config.txt')}")
    print(f"  {time_plot}")
    print(f"  {freq_plot}")
    print("\n" + "="*60)
    print("Filter configuration:")
    print("="*60)
    print(f"  Filter type:     12-tap symmetric linear-phase FIR")
    print(f"  Coefficients:    {COEFF_HALF}")
    print(f"  COEFF_SUM:       {COEFF_SUM}")
    print(f"  RTL latency:     {GOLDEN_OFFSET} clock cycles")
    print(f"  Num samples:     {num_samples}")
    print(f"  Signal type:     {signal_type}")
    print("="*60 + "\n")

    if show_plot:
        plt.figure(figsize=(12, 8))
        plt.plot(time, clean_signal, label="clean")
        plt.plot(time, noisy_signal / DATA_SCALE, label="noisy", alpha=0.7)
        plt.plot(time, filtered_signal / DATA_SCALE, label="filtered", alpha=0.7)
        plt.grid(True)
        plt.legend()
        plt.show()

    return noisy_signal, filtered_signal


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate symmetric FIR test vectors")
    parser.add_argument("--sample-rate", type=int, default=1000)
    parser.add_argument("--signal-freq", type=float, default=10.0)
    parser.add_argument("--noise", type=float, default=0.2)
    parser.add_argument("--num-samples", type=int, default=1000)
    parser.add_argument("--signal-type", default="sine")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--show-plot", action="store_true")
    parser.add_argument("--interactive", action="store_true", help="Prompt for parameters")
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.interactive:
        sample_rate, signal_freq, noise, num_samples, signal_type = get_user_input()
    else:
        sample_rate = args.sample_rate
        signal_freq = args.signal_freq
        noise = args.noise
        num_samples = args.num_samples
        signal_type = args.signal_type

    run_generation(
        sample_rate=sample_rate,
        signal_freq=signal_freq,
        noise_amplitude=noise,
        num_samples=num_samples,
        signal_type=signal_type,
        output_dir=args.output_dir,
        docs_dir=args.docs_dir,
        seed=args.seed,
        show_plot=args.show_plot or args.interactive,
    )


if __name__ == "__main__":
    main()