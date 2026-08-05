"""
Firebase Credentials & Initialization Config
---------------------------------------------
Initializes firebase-admin SDK using service account credentials or environment variables.
Provides fallback mock connection mode when credentials are not yet supplied.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

_app_initialized = False

def init_firebase(cred_path: str = None):
    global _app_initialized
    if _app_initialized:
        return firestore.client()

    if cred_path is None:
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", r"D:\Major proj\firebase\serviceAccountKey.json")

    if os.path.exists(cred_path):
        print(f"[Firebase Config] Initializing Firebase Admin SDK with credentials: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _app_initialized = True
        return firestore.client()
    else:
        print(f"[Firebase Config] Notice: Credential file '{cred_path}' not found.")
        print("[Firebase Config] Operating in Local Offline/Mock Mode for testing.")
        return None
