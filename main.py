import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Aapki Contract List ---
contract_numbers_to_process = [
    "10521258", "9631990", "8703919", "9401473", "10451667", "8993991", "9820501", 
    "9801882", "10575712", "10880086", "10550510", "8655693", "10007434", "9368177", 
    "10211222", "9458825", "9667780", "8341016", "9511092", "8815746", "9195003"
]

def parse_dotnet_date(date_string):
    if date_string and date_string.startswith('/Date('):
        try:
            timestamp_ms = int(date_string.replace('/Date(', '').replace(')/', ''))
            return datetime.fromtimestamp(timestamp_ms / 1000).strftime('%d-%b-%Y').upper()
        except: return date_string
    return date_string

def find_name(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.upper() == "NAME": return v
            res = find_name(v)
            if res: return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_name(item)
            if res: return res
    return None

def fetch_contract_data(contract_no):
    url = "https://commonwebapp.mahindrafs.com/Soa_Clms_Encrypt/api/GeneratePDFController/GenerateSOAPDF_New"
    today = datetime.now().strftime('%d-%b-%Y').upper()
    payload = {
        "acontract_no": contract_no,
        "aafc_rate": "36",
        "aempcode": "23238287",
        "atxtdate": today,
        "modeofSOAGen": "Website",
        "browser": "PythonRequests"
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        response_json = response.json()
        if "Message" in response_json:
            data_for_pdf = json.loads(response_json["Message"])
            customer_name = find_name(data_for_pdf) or "N/A"
            if len(data_for_pdf) > 1 and isinstance(data_for_pdf[1], list):
                last_receipt = data_for_pdf[1][-1]
                last_date = parse_dotnet_date(last_receipt.get('RECEIPT_DATE', 'N/A'))
                return {
                    'contract_no': contract_no,
                    'customer_name': customer_name,
                    'date_received': last_date,
                    'receipt_no': last_receipt.get('RECEIPT_SEQUENCE_NUMBER', 'N/A'),
                    'amount': last_receipt.get('TXN_AMT', 'N/A'),
                    'instr_type': last_receipt.get('INSTR_TYPE_NO', 'N/A'),
                    'is_today': (last_date == today)
                }
    except: pass
    return None

all_results = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_contract_data, cn) for cn in contract_numbers_to_process]
    for f in as_completed(futures):
        res = f.result()
        if res: all_results.append(res)

final_output = {
    "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    "data": all_results
}
with open('data.json', 'w') as f:
    json.dump(final_output, f, indent=4)

print(f"Success! Processed {len(all_results)} contracts.")
