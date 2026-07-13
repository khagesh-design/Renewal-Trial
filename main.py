import os
import re
import pdfplumber
import pandas as pd

# Verified Google Drive Path
PDF_FOLDER = "/content/drive/MyDrive/Iris Blue Agency/Motor/2026/Renewal-2026/July 26/SCH,DN,VIG&CERT"
OUTPUT_FILE = "Compiled_Data.xlsx"

def extract_data():
    if not os.path.exists(PDF_FOLDER):
        print(f"Error: Folder not found at {PDF_FOLDER}")
        return

    # 1. Load existing data to avoid duplicates
    if os.path.exists(OUTPUT_FILE):
        df_existing = pd.read_excel(OUTPUT_FILE)
        processed = set(df_existing['Filename'].tolist())
    else:
        df_existing = pd.DataFrame()
        processed = set()

    all_files = os.listdir(PDF_FOLDER)
    dn_files = [f for f in all_files if f.lower().endswith('.pdf') and '-dn' in f.lower()]
    new_dn_files = [f for f in dn_files if f not in processed]

    if not new_dn_files:
        print("No new files to process.")
        return

    # 2. Extract SCH totals for mapping (Mapping by Plate Number from Filename)
    sch_totals = {}
    sch_files = [f for f in all_files if f.lower().endswith('.pdf') and '-sch' in f.lower()]
    for f in sch_files:
        try:
            plate = f.split('-')[1].strip().upper()
            with pdfplumber.open(os.path.join(PDF_FOLDER, f)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    match = re.search(r'Total\s+Rs\.\s+([\d,]+\.\d{2})', text, re.IGNORECASE)
                    if match:
                        sch_totals[plate] = match.group(1)
                        break
        except: continue

    # 3. Process new DN files
    new_rows = []
    for f in new_dn_files:
        try:
            with pdfplumber.open(os.path.join(PDF_FOLDER, f)) as pdf:
                text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                plate = f.split('-')[1].strip().upper()
                
                entry = {
                    "Filename": f,
                    "Debit Note Number": (re.search(r'DEBIT NOTE NO\s*([A-Z0-9]+)', text, re.I) or re.Match()).group(1) if re.search(r'DEBIT NOTE NO\s*([A-Z0-9]+)', text, re.I) else "N/A",
                    "Policy Number": (re.search(r'PYA\w+', text) or re.Match()).group(0) if re.search(r'PYA\w+', text) else "N/A",
                    "Client Name": (re.search(r'(?:MR|MRS|MS|MISS)\s+(.*?)\s+DEBIT NOTE', text, re.I) or re.Match()).group(1) if re.search(r'(?:MR|MRS|MS|MISS)\s+(.*?)\s+DEBIT NOTE', text, re.I) else "N/A",
                    "Plate Number": plate,
                    "DN Total Amount": (re.search(r'Total Including Levies.*?([\d,]+\.\d{2})', text, re.S|re.I) or re.Match()).group(1) if re.search(r'Total Including Levies.*?([\d,]+\.\d{2})', text, re.S|re.I) else "0.00",
                    "SCH Total Amount": sch_totals.get(plate, "0.00")
                }
                new_rows.append(entry)
        except Exception as e: print(f"Error processing {f}: {e}")

    # 4. Merge and Save
    if new_rows:
        df_final = pd.concat([df_existing, pd.DataFrame(new_rows)], ignore_index=True)
        df_final.to_excel(OUTPUT_FILE, index=False)
        print(f"Successfully added {len(new_rows)} records to {OUTPUT_FILE}.")

if __name__ == "__main__":
    extract_data()
