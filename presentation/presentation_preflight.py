"""
presentation/presentation_preflight.py
---------------------------------------
Automated Preflight Diagnostic & Verification Utility for IEEE 9-Bus Presentation.
Performs comprehensive hardware, software, model, and network checks before startup.
"""

import os
import sys
import json
import socket
import hashlib
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def is_port_open_or_available(host: str, port: int) -> tuple[bool, str]:
    """Checks if a port is responding or bindable."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        s.close()
        return True, "ACTIVE_LISTENER"
    except (socket.timeout, ConnectionRefusedError, OSError):
        s.close()
        # Test if bindable
        try:
            b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            b.bind((host, port))
            b.close()
            return True, "AVAILABLE_FREE"
        except OSError:
            return False, "PORT_CONFLICT"

def run_preflight() -> dict:
    results = {
        "status": "PASS",
        "timestamp": None,
        "checks": {}
    }

    # 1. Python Environment Check
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    py_ok = (py_ver.major == 3 and py_ver.minor >= 10)
    results["checks"]["python_version"] = {
        "value": py_str,
        "status": "PASS" if py_ok else "FAIL",
        "remedy": "Install Python 3.10+ (Recommended: Python 3.11, 3.12, 3.14)" if not py_ok else None
    }

    # 2. Dependency Imports Check
    deps = ["numpy", "scipy", "pandas", "sklearn", "matplotlib", "requests"]
    missing_deps = []
    for d in deps:
        try:
            __import__(d)
        except ImportError:
            missing_deps.append(d)

    deps_ok = len(missing_deps) == 0
    results["checks"]["dependencies"] = {
        "value": "All core scientific libraries available" if deps_ok else f"Missing: {missing_deps}",
        "status": "PASS" if deps_ok else "FAIL",
        "remedy": f"pip install -r requirements.txt (Missing: {', '.join(missing_deps)})" if not deps_ok else None
    }

    # 3. Model Weights & Scaler Hash Check
    weights_p = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models", "candidate_mlp_weights.json")
    scaler_p = os.path.join(PROJECT_ROOT, "experiments", "phase4c", "models", "scaler_phase4c_params.json")

    weights_ok = False
    scaler_ok = False
    if os.path.exists(weights_p) and os.path.exists(scaler_p):
        w_h = compute_sha256(weights_p)
        s_h = compute_sha256(scaler_p)
        expected_w = "F0FEBD5B3829677AC0F2C13262CCCB5FF8947CDCB59596F5E4A8F2B6180C27C5"
        expected_s = "76D0AD26E730D19776D20E70055CC6D490F2AAD4680BFD47DF0D95689888FC6D"
        weights_ok = (w_h == expected_w)
        scaler_ok = (s_h == expected_s)

    model_ok = weights_ok and scaler_ok
    results["checks"]["ml_model_integrity"] = {
        "value": "Phase 4C MLP & Scaler SHA-256 match frozen baseline" if model_ok else "Model checksum mismatch",
        "status": "PASS" if model_ok else "FAIL",
        "remedy": "Restore candidate_mlp_weights.json and scaler_phase4c_params.json from git branch" if not model_ok else None
    }

    # 4. Simulink Models Verification
    working_mdl_p = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_DISTURBANCES.slx")
    protected_mdl_p = os.path.join(PROJECT_ROOT, "IEEE_9bus", "IEEE_9bus_PQD_HIL_R2025a.slx")

    working_exists = os.path.exists(working_mdl_p)
    protected_exists = os.path.exists(protected_mdl_p)
    protected_hash_ok = False
    if protected_exists:
        p_h = compute_sha256(protected_mdl_p)
        expected_p = "5D833D8FDC5086B7BEC437A30A7829B4EA6D1B9BEFA93DF75E7CA0631BEB084D"
        protected_hash_ok = (p_h == expected_p)

    simulink_ok = working_exists and protected_exists and protected_hash_ok
    simulink_remedy = None
    if not protected_hash_ok:
        simulink_remedy = "Restore IEEE_9bus_PQD_HIL_R2025a.slx from git commit to maintain protected reference"
    elif not (working_exists and protected_exists):
        simulink_remedy = "Simulink model files missing in IEEE_9bus/"

    results["checks"]["simulink_models"] = {
        "value": "Working and Protected reference models verified" if simulink_ok else "Model files missing or altered",
        "status": "PASS" if simulink_ok else "FAIL",
        "remedy": simulink_remedy
    }

    # 5. MATLAB Installation & Detection
    matlab_exe = shutil.which("matlab")
    common_matlab_paths = [
        r"C:\Program Files\MATLAB\R2025a\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2024b\bin\matlab.exe",
        r"C:\Program Files\MATLAB\R2024a\bin\matlab.exe"
    ]
    if not matlab_exe:
        for p in common_matlab_paths:
            if os.path.exists(p):
                matlab_exe = p
                break

    matlab_detected = matlab_exe is not None
    results["checks"]["matlab_environment"] = {
        "value": f"Detected: {matlab_exe}" if matlab_detected else "MATLAB executable not found on system PATH",
        "status": "PASS" if matlab_detected else "WARNING",
        "remedy": "Add MATLAB to system PATH or specify MATLAB_EXECUTABLE in presentation/presentation_config.json" if not matlab_detected else None
    }

    # 6. Backend and Telemetry Ports Check
    port_8500_ok, p8500_state = is_port_open_or_available("127.0.0.1", 8500)
    port_8502_ok, p8502_state = is_port_open_or_available("127.0.0.1", 8502)
    ports_ok = port_8500_ok and port_8502_ok
    results["checks"]["network_ports"] = {
        "value": f"Port 8500: {p8500_state}, Port 8502: {p8502_state}",
        "status": "PASS" if ports_ok else "FAIL",
        "remedy": "Terminate conflicting processes on port 8500/8502 using scripts/stop_presentation.ps1" if not ports_ok else None
    }

    # 7. Frontend Assets Check
    fe_files = [
        os.path.join(PROJECT_ROOT, "web", "index.html"),
        os.path.join(PROJECT_ROOT, "web", "app.js"),
        os.path.join(PROJECT_ROOT, "web", "styles.css")
    ]
    fe_ok = all(os.path.exists(p) for p in fe_files)
    results["checks"]["frontend_assets"] = {
        "value": "All dashboard UI files present (index.html, app.js, styles.css)",
        "status": "PASS" if fe_ok else "FAIL",
        "remedy": "Check web/ directory integrity" if not fe_ok else None
    }

    # Evaluate Overall Status
    failures = [k for k, v in results["checks"].items() if v["status"] == "FAIL"]
    warnings = [k for k, v in results["checks"].items() if v["status"] == "WARNING"]

    if failures:
        results["status"] = "FAIL"
    elif warnings:
        results["status"] = "PASS_WITH_WARNINGS"
    else:
        results["status"] = "PASS"

    return results

def print_preflight_report(results: dict):
    print("=" * 80)
    print("   IEEE 9-BUS POWER QUALITY BENCH — PREFLIGHT VERIFICATION REPORT")
    print("=" * 80)
    for name, item in results["checks"].items():
        st = item["status"]
        val = item["value"]
        badge = "[  OK  ]" if st == "PASS" else ("[ WARN ]" if st == "WARNING" else "[ FAIL ]")
        print(f" {badge} {name:25s} : {val}")
        if item.get("remedy"):
            print(f"         -> Action Required: {item['remedy']}")
    print("-" * 80)
    print(f" OVERALL PREFLIGHT READINESS: {results['status']}")
    print("=" * 80)

if __name__ == "__main__":
    rep = run_preflight()
    print_preflight_report(rep)
    sys.exit(0 if rep["status"] in ("PASS", "PASS_WITH_WARNINGS") else 1)
