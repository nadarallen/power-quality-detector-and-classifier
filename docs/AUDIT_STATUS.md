# Audit Status & Gate Control
# ------------------------------------------------------------------------------
# Hard Gate Control for ML & Downstream Development
# Rule: ready_for_ml_phase can ONLY become true when ALL sections PASS
#       and blocking_issues is empty.
# ------------------------------------------------------------------------------

audit_status: NOT_COMPLETE

repository_audit: PASS
standards_audit: PASS
parameter_audit: PASS
generator_audit: PASS
dataset_audit: PASS
python_esp32_audit: FAIL

blocking_issues:
  - issue_id: "BLOCKER-01"
    subsystem: "firmware/src/feature_extraction.cpp"
    title: "ESP32 Goertzel Frequency-Bin Attenuation & THD Discrepancy"
    description: "Frequency bin index k is declared as float (float k = 0.5f + ...) without integer cast. Shifting target frequency by +2.5 Hz (evaluates at 52.5 Hz instead of 50.0 Hz). Causes 37.89% fundamental magnitude attenuation and up to 16.71% absolute THD error against Python baseline."
    remediation_required: "Change to int k = (int)(0.5f + (length * target_freq / sample_rate));"

  - issue_id: "BLOCKER-02"
    subsystem: "web/app.js"
    title: "Incorrect Disturbance Definition for Interruption in Web Simulator"
    description: "web/app.js line 122 sets Interruption to val *= 0.680 (0.68 pu), which violates IEEE 1159 Clause 3.1.34 (< 0.10 pu). Generates a Voltage Sag rather than an Interruption."
    remediation_required: "Update web/app.js line 122 from val *= 0.680 to val *= 0.05 (or complete cutoff 0.0)."

  - issue_id: "BLOCKER-03"
    subsystem: "firmware/src/inference.cpp"
    title: "Stubbed Out Embedded Neural Network Inference Engine"
    description: "runInference() runs a hardcoded if-else heuristic rule rather than invoking tflite::MicroInterpreter::Invoke() on g_model. Heuristic omits Flicker and Notch entirely."
    remediation_required: "Wire real TFLite Micro runtime to invoke model_data.h and evaluate probabilities."

  - issue_id: "BLOCKER-04"
    subsystem: "dsp/waveform_generator.py"
    title: "Constrained Parameter Bounds Omit IEEE 1159 Boundary Regimes"
    description: "Sag depth [0.35, 0.85] omits severe sags (0.10 - 0.35 pu). Swell magnitude [1.15, 1.65] omits severe swells (1.65 - 1.80 pu). Harmonics omits even orders (H2, H4) and higher odd orders (H9, H11)."
    remediation_required: "Update bounds in dsp/waveform_generator.py to align with config/pqd_parameter_spec.yaml."

  - issue_id: "BLOCKER-05"
    subsystem: "Dataset/BARC DATA.csv"
    title: "Synthetic Duration Shortcut & Dead Frequency Feature"
    description: "All 985 Transients have Duration_ms == 5.0 ms exactly (synthetic shortcut). Dominant_Freq_Hz is completely dead (50.000 Hz constant across all 10,000 samples). Severe class imbalance (7.83:1) vs claimed balanced."
    remediation_required: "Train raw waveform 1D CNN to bypass 5.0 ms tabular shortcut; apply inverse class weighting."

ready_for_ml_phase: false
