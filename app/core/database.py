import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from app.core.config import settings

def initialize_firebase():
    if not firebase_admin._apps:
        cred_value = settings.FIREBASE_CREDENTIALS
        
        try:
            # OPTION 1: Value is a raw JSON string (Common for Cloud ENV)
            if cred_value and cred_value.startswith('{'):
                cred_dict = json.loads(cred_value)
                cred = credentials.Certificate(cred_dict)
            # OPTION 2: Value is a path to a JSON file
            elif cred_value and os.path.exists(cred_value):
                cred = credentials.Certificate(cred_value)
            # OPTION 3: Fallback to Google Application Default Credentials
            else:
                cred = credentials.ApplicationDefault()
            
            firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID
            })
        except Exception as e:
            # Final fallback if credentials still fail - try to init with just project ID
            # This is often needed in certain restricted environments
            try:
                firebase_admin.initialize_app(options={
                    "projectId": settings.FIREBASE_PROJECT_ID
                })
            except:
                raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {str(e)}")

initialize_firebase()
db = firestore.client()