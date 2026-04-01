import requests
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- MEMORY ----------------
def load_history():
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return {str(item['contract_no']): item for item in data}
        except:
            return {}
    return {}

def is_full_number(num):
    s = str(num).strip()
    return s and not s.startswith("000000") and s != "N/A" and len(s) >= 10

HISTORY = load_history()

# ---------------- SESSION ----------------
def create_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2,
                    status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

SESSION = create_session()

# ---------------- SCRAPER ----------------
def get_data(contract_no):
    time.sleep(2)

    current_hour = datetime.now().hour
    is_night = (0 <= current_hour < 7)

    old = HISTORY.get(str(contract_no))
    old_co = old.get("co_mobile_number") if old else None

    # ❌ Case: N/A → never retry
    if old and (old_co == "N/A" or old_co == ""):
        return old

    # ❌ Case: full → never retry
    if old and is_full_number(old_co):
        return old

    # ❌ Case: day + masked → skip
    if old and not is_night:
        return old

    # -------- SCRAPE --------
    url = f"http://crm.mahindrafs.com:9070/CustomerStat/CustomerStatCard?userid=23238287&ContractNo={contract_no}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        resp = SESSION.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")

        emi_tag = soup.find("input", {"name": "Emiamount"})
        date_tag = soup.find("input", {"name": "EMIdate"})
        mob_tag = soup.find("span", {"id": "lblBorrowerMobile"}) or soup.find("input", {"name": "mobileno"})
        co_tag = soup.find("span", {"id": "lblCoBorrowerMobile"})

        emi = emi_tag.get("value", "N/A") if emi_tag else "N/A"

        day = "N/A"
        if date_tag and date_tag.get("value"):
            try:
                day = datetime.strptime(date_tag["value"], "%d-%b-%Y").day
            except:
                pass

        mobile = "N/A"
        if mob_tag:
            mobile = mob_tag.get("value") or mob_tag.get_text(strip=True)

        co_mobile = co_tag.get_text(strip=True) if co_tag else ""

        # -------- CLEAN LOGIC --------
        if not co_mobile:
            co_mobile = "N/A"

        # अगर पहले full है तो overwrite मत करो
        if old and is_full_number(old_co):
            co_mobile = old_co

        return {
            "contract_no": contract_no,
            "mobile_number": mobile,
            "emi_amount": emi,
            "emi_day": day,
            "co_mobile_number": co_mobile
        }

    except:
        return old if old else None

# ---------------- MAIN ----------------
def main():
    CONTRACT_IDS = [
        "10521258","9631990","8703919","9401473","10451667","8993991",
        "9820501","9801882","10575712","10880086","10550510","8655693",
        "10007434","9368177","10211222","9458825","9667780","8341016",
        "9511092","8815746","9195003","8727962"
    ]

    results = []
    new_history = {str(k): v for k, v in HISTORY.items()}

    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(get_data, cid): cid for cid in CONTRACT_IDS}

        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)
                new_history[str(res["contract_no"])] = res

    # -------- SAVE --------
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(list(new_history.values()), f, indent=4)

    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("\n\n### Contract Details\n\n")
        f.write("Here is a table showing the requested details:\n\n")

        header = f"{'Contract No':<12} {'Mobile No':<15} {'EMI Amount':<12} {'EMI Day':<9} {'Co-Borrower Mobile':<20}"
        f.write(header + "\n")
        f.write("-" * 70 + "\n")

        for r in results:
            f.write(f"{r['contract_no']:<12} {r['mobile_number']:<15} {r['emi_amount']:<12} {r['emi_day']:<9} {r['co_mobile_number']:<20}\n")

    print("✅ All files updated successfully")

if __name__ == "__main__":
    main()
