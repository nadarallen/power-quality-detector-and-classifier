import hashlib
import json

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

model_hash = get_sha256('experiments/phase4c/models/candidate_mlp_weights.json')
scaler_hash = get_sha256('experiments/phase4c/models/scaler_phase4c_params.json')
ref_slx_hash = get_sha256('IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx')
dist_slx_hash = get_sha256('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx')

print(f"CANDIDATE_MODEL_SHA256: {model_hash}")
print(f"SCALER_PARAMS_SHA256:   {scaler_hash}")
print(f"REF_HIL_SLX_SHA256:     {ref_slx_hash}")
print(f"DIST_SLX_SHA256:        {dist_slx_hash}")
