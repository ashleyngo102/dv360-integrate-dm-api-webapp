import hashlib
import re
import csv
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import List, Optional

def clean_header_fuzzy(h: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(h).lower())

def clean_header(h: str) -> str:
    return clean_header_fuzzy(h)

def parse_xlsx_manual(file_bytes: bytes) -> List[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            try:
                shared_strings_xml = z.read('xl/sharedStrings.xml')
                root_strings = ET.fromstring(shared_strings_xml)
                ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                strings = [t.text for t in root_strings.findall('.//ns:t', ns)]
            except KeyError:
                strings = []

            sheet_xml = z.read('xl/worksheets/sheet1.xml')
            root_sheet = ET.fromstring(sheet_xml)
            
            rows = []
            for r in root_sheet.findall('.//ns:row', ns):
                row_data = []
                for c in r.findall('.//ns:c', ns):
                    v = c.find('ns:v', ns)
                    if v is None:
                        row_data.append('')
                        continue
                    v_text = v.text
                    if c.get('t') == 's':
                        try:
                            idx = int(v_text)
                            if idx < len(strings):
                                row_data.append(strings[idx])
                            else:
                                row_data.append('')
                        except (ValueError, TypeError):
                            row_data.append('')
                    else:
                        row_data.append(v_text)
                rows.append(row_data)
        
        if not rows:
            return []
            
        headers = [str(col).strip() for col in rows[0]]
        records = []
        for row in rows[1:]:
            if not any(row): continue
            record = {}
            for i, h in enumerate(headers):
                if i < len(row):
                    record[h] = str(row[i]).strip()
                else:
                    record[h] = ''
            records.append(record)
        return records

    except zipfile.BadZipFile:
        # Fallback to CSV!
        try:
            text = file_bytes.decode('utf-8')
            f = io.StringIO(text)
            reader = csv.DictReader(f)
            return list(reader)
        except Exception as e:
            print(f"Fallback to CSV parsing failed: {e}")
            return []
    except Exception as e:
        print(f"Error parsing XLSX: {e}")
        return []

def test_mapping_logic():
    with open('/Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/Mock_Data_Sheet_Mapping_100.xlsx', 'rb') as f:
        file_bytes = f.read()
    
    records = parse_xlsx_manual(file_bytes)
    print("Top 5 parsed records (Unhashed):")
    for i in range(min(5, len(records))):
        print(records[i])
    
    from main import format_and_hash
    print("\nTop 5 hashed payloads (Pre-ingest):")
    for i in range(min(5, len(records))):
        rec = records[i]
        email_hashed = format_and_hash(rec.get('email'), 'email') if rec.get('email') else None
        first_hashed = format_and_hash(rec.get('first_name'), 'first_name') if rec.get('first_name') else None
        last_hashed = format_and_hash(rec.get('last_name'), 'last_name') if rec.get('last_name') else None
        print(f"Row {i+1} - Email: {email_hashed}, First: {first_hashed}, Last: {last_hashed}")
    
    assert len(records) == 100
    
    active_keys = records[0].keys()
    headers_cleaned = {clean_header_fuzzy(k): k for k in active_keys}
    
    col_map = {
        "email": None, "phone": None, "first_name": None,
        "last_name": None, "zip_code": None, "country": None
    }
    
    for ck, k in headers_cleaned.items():
        if "email" in ck or "mail" in ck: col_map["email"] = k
        elif "phone" in ck or "mobile" in ck or "cell" in ck or "tel" in ck: col_map["phone"] = k
        elif "first" in ck or "given" in ck or "fname" in ck or "first_name" in ck: col_map["first_name"] = k
        elif "last" in ck or "family" in ck or "lname" in ck or "surname" in ck or "last_name" in ck: col_map["last_name"] = k
        elif "zip" in ck or "postal" in ck or "postcode" in ck or "zip_code" in ck: col_map["zip_code"] = k
        elif "country" in ck or "region" in ck or "nation" in ck: col_map["country"] = k

    print("Mapping succeeded effortlessly!")
    print(f"Mapped headers: {col_map}")
    
    assert col_map["email"] is not None
    assert col_map["first_name"] is not None

if __name__ == '__main__':
    test_mapping_logic()
    print("All tests passed!")
