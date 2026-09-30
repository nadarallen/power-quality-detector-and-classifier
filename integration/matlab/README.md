# MATLAB/Simulink R2025a to Python PQD Integration Bridge

## Overview
This directory contains the production-grade acquisition bridge connecting the **IEEE 9-Bus Simulink Electrical Simulation** (`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`) to the existing **Python Power Quality Disturbance (PQD) backend**, DSP pipeline, ML inference, and web dashboard.

## Architecture

```
+------------------------------------+
|  MATLAB / Simulink R2025a          |
|  IEEE_9bus_PQD_HIL_R2025a.slx     |
|  Bus 5: Vabc_5 (pu) & Iabc_5 (pu)  |
+-----------------+------------------+
                  | Continuous Logging (~1.126 MHz)
                  v
+------------------------------------+
|  resample() Anti-Aliasing Filter   |
|  f_cutoff = 2200 Hz, Fs = 5000 Hz  |
+-----------------+------------------+
                  | Resampled 5000 Hz Synchronized Matrices
                  v
+------------------------------------+
|  pqd_stream_client.m               |
|  Batching (1000 samples = 200 ms)  |
+-----------------+------------------+
                  | Direct Localhost HTTP POST (JSON)
                  v
+------------------------------------+
|  Python Server (server.py)         |
|  POST /api/ingest/simulink         |
+-----------------+------------------+
                  |
                  v
+------------------------------------+
|  RealtimePQPipeline                |
|  - MultiChannelRingBuffer (60 Hz)  |
|  - 3-Phase Event Engine            |
|  - Enhanced DSP (Goertzel Harmonics)|
|  - Real ML Model Inference         |
|  - Domain Mismatch Guard           |
|  - SQLite Event Persistence        |
+-----------------+------------------+
                  |
                  v
+------------------------------------+
|  Existing Retro Web Dashboard      |
|  SSE Stream /api/stream/telemetry  |
+------------------------------------+
```

## Non-Negotiable Integration Rules
1. **Electrical Integrity Preserved**: The IEEE 9-bus network (generators, lines, transformers, powergui) remains strictly unchanged.
2. **Frequency Preserved**: System operates at native 60 Hz.
3. **No CSV Transport**: All data moves memory-to-API via batched HTTP requests.
4. **Anti-Aliasing Resampling**: Signal Processing Toolbox `resample()` downsamples continuous simulation data from ~1.1 MHz to 5000 Hz with linear phase polyphase filtering.
5. **Real ML Evaluation**: Python evaluates the actual trained neural network; normal 60 Hz steady-state power flow reports `MODEL_DOMAIN_MISMATCH` with genuine probabilities rather than hardcoded mock predictions.

## Usage

### Step 1: Start the Python Backend Server
In a terminal, start the Python server:
```powershell
python server.py 8500
```

### Step 2: Run the Simulation Bridge from MATLAB
In MATLAB (R2025a):
```matlab
cd 'd:\my study\Project\power-quality-detector-and-classifier\integration\matlab'
start_pqd_stream
```
Or customize parameters:
```matlab
summary = run_simulink_pqd('stop_time', 0.4, 'batch_size', 1000);
```

### Step 3: View Real-Time Results on Web Dashboard
Open your browser at:
`http://localhost:8500`

The dashboard will display:
- Acquisition Source: `simulink`
- Device ID: `SIMULINK_IEEE9BUS_BUS5`
- Sampling Rate: `5000 Hz`
- Nominal Frequency: `60.0 Hz`
- Waveforms: Synchronized 3-phase waveforms ($V_a$, $V_b$, $V_c$)
- Spectrum: 60 Hz harmonic series ($60, 120, 180, \dots$)
- System Status: `NORMAL` (no false disturbance triggers)
