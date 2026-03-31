import requests
import json
import re
import datetime
import concurrent.futures
import os

# --- ASLI MAHINDRA CONFIG (Copilot ne yahan galti ki thi) ---
API_URL = "https://commonwebapp.mahindrafs.com/Soa_Clms_Encrypt/api/GeneratePDFController/GenerateSOAPDF_New"

CONTRACT_IDS = [
    "10521258","9631990","8703919","9401473","10451667","8993991","9820501","9801882",
    "10575712","10880086","10550510","8655693","10007434","9368177","10211222","9458825",
    "9667780","8341016","9511092","8815746","9195003"
]

def make_payload(contract_id):
    # Jo aapke purane code mein payload tha, wahi yahan dalna zaroori hai
    return {
        "acontract_no": contract_id,
        "aafc_rate": "36",
        "aempcode": "23238287",
        "atxtdate": datetime.datetime.now().strftime('%d-%b-%Y').upper(),
        "modeofSOAGen": "Website",
        "browser": "PythonRequests"
    }

# --- Date Parsing Logic ---
DOTNET_DATE_RE = re.compile(r'/Date\((?P<ms>-?\d+)(?:[+-]\d+)?\)/')

def parse_date(match):
    ms = int(match.group('ms'))
    dt = datetime.datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime('%d-%b-%Y').upper()

def convert_dates(obj):
    if isinstance(obj, str):
        return DOTNET_DATE_RE.sub(lambda m: parse_date(m), obj)
    elif isinstance(obj, list):
        return [convert_dates(v) for v in obj]
    elif isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    return obj

def fetch_receipt(contract_id):
    try:
        resp = requests.post(API_URL, json=make_payload(contract_id), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        # API ka "Message" part extract karna (jo aapke purane code mein tha)
        if "Message" in data:
            message_content = json.loads(data["Message"])
            return {"contract_id": contract_id, "success": True, "data": convert_dates(message_content)}
        return {"contract_id": contract_id, "success": False, "error": "No Message in response"}
    except Exception as e:
        return {"contract_id": contract_id, "success": False, "error": str(e)}

def main():
    results = []
    print(f"Fetching {len(CONTRACT_IDS)} contracts...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_receipt, cid): cid for cid in CONTRACT_IDS}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    output = {
        "update_time": datetime.datetime.now().isoformat(),
        "receipts": results
    }
    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Done! data.json updated.")

if __name__ == "__main__":
    main()
