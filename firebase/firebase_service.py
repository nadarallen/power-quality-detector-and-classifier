"""
Firebase Database Service Manager
---------------------------------
Handles uploading disturbance events, telemetry points, and benchmark metrics to Firebase DB / Firestore collections:
- Collection 'events': Live telemetry disturbance logs
- Collection 'benchmarks': Multi-model comparison evaluation metrics
"""

import os
import sys
import time
from typing import Dict, Any
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase.firebase_config import init_firebase


class FirebaseDBService:
    def __init__(self, cred_path: str = None):
        self.db = init_firebase(cred_path)

    def is_connected(self) -> bool:
        return self.db is not None

    def log_disturbance_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Logs a single PQD classification event to 'events' collection.
        """
        event_data['timestamp_server'] = time.time()

        if self.db:
            try:
                doc_ref = self.db.collection('events').document()
                doc_ref.set(event_data)
                print(f"[Firebase DB] Saved event {doc_ref.id} -> {event_data.get('predicted_class')}")
                return True
            except Exception as e:
                print(f"[Firebase DB Error] Failed to upload event: {e}")
                return False
        else:
            print(f"[Firebase Mock Log] Event -> {event_data}")
            return True

    def upload_benchmark_report(self, report_df_records: list) -> bool:
        """
        Uploads model comparison benchmark summary records to 'benchmarks' collection.
        """
        if self.db:
            try:
                batch = self.db.batch()
                for rec in report_df_records:
                    doc_ref = self.db.collection('benchmarks').document(rec.get('model', 'unknown'))
                    rec['updated_at'] = time.time()
                    batch.set(doc_ref, rec)
                batch.commit()
                print(f"[Firebase DB] Successfully uploaded {len(report_df_records)} benchmark records.")
                return True
            except Exception as e:
                print(f"[Firebase DB Error] Benchmark upload error: {e}")
                return False
        else:
            print(f"[Firebase Mock Log] Uploaded {len(report_df_records)} benchmark rows to mock DB.")
            return True


if __name__ == "__main__":
    fb = FirebaseDBService()
    test_event = {
        'timestamp': 1000,
        'true_state': 'Sag',
        'predicted_class': 'Sag',
        'confidence': 0.94,
        'rms_voltage': 0.65,
        'thd': 1.2
    }
    fb.log_disturbance_event(test_event)
