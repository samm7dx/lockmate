#!/usr/bin/env python3
"""Test full upload and processing flow."""

import os
import sys
import time
import threading
import requests
import uvicorn
from secret_wards.api.server import app

def test_upload_processing():
    # Set secret (32 bytes base64)
    os.environ["RAKSHA_SECRET"] = "/2R4JyyAqfYl1kPwSWX0IkA/jsSdNH6F4TGM3FezXxU="
    
    # Start server in background thread
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    base_url = "http://127.0.0.1:8000"
    
    try:
        # Create a test CSV file
        test_csv = """patient_name,phone,aadhaar,diagnosis,medication
Rahul Sharma,9876543210,123456789012,Diabetes,Metformin 500mg
Priya Patel,8765432109,234567890123,Hypertension,Amlodipine 5mg
"""
        
        # Test upload
        print("Testing file upload...")
        files = {'files': ('test_patients.csv', test_csv, 'text/csv')}
        data = {'config_path': 'config/policy.yaml'}
        
        resp = requests.post(f"{base_url}/api/process", files=files, data=data, timeout=10)
        print(f"  Upload status: {resp.status_code}")
        result = resp.json()
        print(f"  Response: {result}")
        
        job_id = result.get('job_id')
        if not job_id:
            print("  No job_id returned!")
            return False
        
        # Poll for completion
        print(f"\nPolling job {job_id}...")
        for i in range(60):  # Max 60 seconds
            time.sleep(1)
            resp = requests.get(f"{base_url}/api/runs/{job_id}", timeout=5)
            job = resp.json()
            status = job.get('status')
            stage = job.get('stage')
            progress = job.get('progress', {})
            
            print(f"  [{i+1}s] Status: {status}, Stage: {stage}, Records: {progress.get('records_processed', 0)}")
            
            if status == 'completed':
                print(f"\n  Job completed successfully!")
                
                # Test report download
                print("  Testing report download...")
                resp = requests.get(f"{base_url}/api/runs/{job_id}/report", timeout=10)
                print(f"    Report status: {resp.status_code}")
                if resp.status_code == 200:
                    report = resp.json()
                    print(f"    Files sanitized: {report.get('report', {}).get('counts', {}).get('files_sanitized', 0)}")
                    print(f"    Records processed: {report.get('report', {}).get('counts', {}).get('records_processed', 0)}")
                
                # Test records download
                print("  Testing records download...")
                resp = requests.get(f"{base_url}/api/runs/{job_id}/records", timeout=10)
                print(f"    Records status: {resp.status_code}")
                if resp.status_code == 200:
                    lines = resp.text.strip().split('\n')
                    print(f"    Records lines: {len(lines)}")
                
                # Test sanitized download
                print("  Testing sanitized ZIP download...")
                resp = requests.get(f"{base_url}/api/runs/{job_id}/download", timeout=10)
                print(f"    ZIP status: {resp.status_code}")
                if resp.status_code == 200:
                    print(f"    ZIP size: {len(resp.content)} bytes")
                
                return True
                
            elif status == 'failed':
                print(f"\n  Job failed: {job.get('error')}")
                return False
        
        print("  Timeout waiting for completion")
        return False
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_upload_processing()
    sys.exit(0 if success else 1)