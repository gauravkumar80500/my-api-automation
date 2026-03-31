import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# --- Configuration ---
CONTRACT_IDS = [
    "10521258", "9631990", "8703919", "9401473", "10451667", "8993991", "9820501", 
    "9801882", "10575712", "10880086", "10550510", "8655693", "10007434", "9368177", 
    "10211222", "9458825", "9667780", "8341016", "9511092", "8815746", "9195003", "8727962"
]

def parse_dotnet_date(date_string):
    if date_string and date_string.startswith('/Date('):
        try:
            ts = int(date_string.replace('/Date(', '').replace(')/', ''))
            return datetime.fromtimestamp(ts / 1000).strftime('%d-%b-%Y').upper()
        except: return date_string
    return date_string

def get_detailed_info(contract_no, userid):
    url = f"http://crm.mahindrafs.com:9070/CustomerStat/CustomerStatCard?userid={userid}&ContractNo={contract_no}"
    info = {"emi": "N/A", "day": "N/A", "mob": "N/A", "co_mob": "N/A", "guar_mob": "N/A"}
    try:
        resp = requests.get(url, timeout=25)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        emi_tag = soup.find('input', {'name': 'Emiamount'})
        date_tag = soup.find('input', {'name': 'EMIdate'})
        mob_tag = soup.find('span', {'id': 'lblBorrowerMobile'}) or soup.find('input', {'name': 'mobileno'})
        co_mob_tag = soup.find('span', {'id': 'lblCoBorrowerMobile'})
        guar_mob_tag = soup.find('span', {'id': 'lblGuarantorMobile'})

        if emi_tag: info["emi"] = emi_tag.get('value', 'N/A')
        if date_tag and date_tag.get('value'):
            try: info["day"] = datetime.strptime(date_tag['value'], '%d-%b-%Y').day
            except: pass
        if mob_tag: info["mob"] = mob_tag.get('value') or mob_tag.get_text(strip=True)
        if co_mob_tag: info["co_mob"] = co_mob_tag.get_text(strip=True)
        if guar_mob_tag: info["guar_mob"] = guar_mob_tag.get_text(strip=True)
    except: pass
    return info

def fetch_contract_data(contract_no):
    api_url = "https://commonwebapp.mahindrafs.com/Soa_Clms_Encrypt/api/GeneratePDFController/GenerateSOAPDF_New"
    today_str = datetime.now().strftime('%d-%b-%Y').upper()
    userid = "23238287"
    
    scraped = get_detailed_info(contract_no, userid)
    payload = {
        "acontract_no": contract_no, "aafc_rate": "36", "aempcode": userid,
        "atxtdate": today_str, "modeofSOAGen": "Website", "browser": "PythonRequests"
    }
    
    try:
        resp = requests.post(api_url, json=payload, timeout=25)
        msg = json.loads(resp.json()["Message"])
        name = "N/A"
        # Find Customer Name
        if isinstance(msg, list):
            for section in msg:
                if isinstance(section, list):
                    for item in section:
                        if 'NAME' in item:
                            name = item['NAME']
                            break
        
        # Get Latest Receipt
        last_rec = msg[1][-1] if len(msg) > 1 and msg[1] else {}
        rec_date = parse_dotnet_date(last_rec.get('RECEIPT_DATE'))
        
        return {
            "contract_no": contract_no,
            "name": name,
            "date_received": "Today" if rec_date == today_str else rec_date,
            "receipt_no": last_rec.get('RECEIPT_SEQUENCE_NUMBER', 'N/A'),
            "amount": last_rec.get('TXN_AMT', 'N/A'),
            "emi_amount": scraped["emi"],
            "emi_day": scraped["day"],
            "mobile": scraped["mob"],
            "co_mobile": scraped["co_mob"],
            "guar_mobile": scraped["guar_mob"],
            "instr_type": last_rec.get('INSTR_TYPE_NO', 'N/A'),
            "is_today": (rec_date == today_str)
        }
    except Exception as e:
        print(f"Error fetching {contract_no}: {e}")
        return None

def main():
    results = []
    # Setting worker to 1 to prevent connection blocking on GitHub
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(fetch_contract_data, cid) for cid in CONTRACT_IDS]
        for f in as_completed(futures):
            res = f.result()
            if res: results.append(res)
    
    # Save for APK
    with open('data.json', 'w') as f:
        json.dump(results, f, indent=4)
    
    # Save Human Readable Report
    header = f"{'Contract No':<12} {'NAME':<30} {'Date Received':<15} {'Receipt No':<18} {'Amount':<10} {'EMI Amount':<12} {'EMI Day':<9} {'Mobile No':<15} {'Co-Borrower':<15} {'Guarantor':<15} {'Instr Type':<15}"
    sep = "-" * 210
    
    with open('report.txt', 'w', encoding='utf-8') as f:
        f.write(f"Last Updated (IST): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("### Today's Receipts\n")
        f.write(header + "\n" + sep + "\n")
        for r in results:
            if r['is_today']:
                f.write(f"{r['contract_no']:<12} {r['name']:<30} {'Today':<15} {r['receipt_no']:<18} {r['amount']:<10} {r['emi_amount']:<12} {r['emi_day']:<9} {r['mobile']:<15} {r['co_mobile']:<15} {r['guar_mobile']:<15} {r['instr_type']:<15}\n")
        
        f.write("\n\n### All Receipts\n")
        f.write(header + "\n" + sep + "\n")
        for r in results:
            f.write(f"{r['contract_no']:<12} {r['name']:<30} {r['date_received']:<15} {r['receipt_no']:<18} {r['amount']:<10} {r['emi_amount']:<12} {r['emi_day']:<9} {r['mobile']:<15} {r['co_mobile']:<15} {r['guar_mobile']:<15} {r['instr_type']:<15}\n")

    print("Success! data.json and report.txt updated.")

if __name__ == "__main__":
    main()
