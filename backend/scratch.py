import librosa
import numpy as np

def analyze(y, name):
    y_norm = librosa.util.normalize(y)
    rms = np.mean(librosa.feature.rms(y=y))
    rms_norm = np.mean(librosa.feature.rms(y=y_norm))
    sc = np.mean(librosa.feature.spectral_centroid(y=y_norm))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=y_norm))
    print(f"[{name}] RMS: {rms:.4f}, Norm RMS: {rms_norm:.4f}, SC: {sc:.2f}, ZCR: {zcr:.4f}")

sr = 22050
y_sine = np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr))
analyze(y_sine, "Sine Wave")

y_noise = np.random.randn(sr)
analyze(y_noise, "White Noise")
