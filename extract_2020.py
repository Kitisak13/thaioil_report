import os
import time
import base64
import json
import csv
import requests

# ==================== CONFIGURATION ====================
def load_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key and os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1].strip("\'\"")
    return key or "YOUR_GEMINI_API_KEY_HERE"

API_KEY = load_api_key()
MODEL_NAME = "gemini-3.1-flash-lite"
INPUT_DIR = os.path.join("thaioil_reports", "2020")
OUTPUT_FILE = "oil_prices_and_factors_2020.csv"
RPM_LIMIT = 15  # จำกัด 15 requests ต่อนาที (ใช้หน่วงเวลา ~4.5 - 5 วินาทีต่อไฟล์)
# =======================================================

# JSON Schema สำหรับกำหนดโครงสร้างผลลัพธ์ของ Daily Report ปี 2020
JSON_SCHEMA = {
  "type": "object",
  "properties": {
    "report_date": {
      "type": "string",
      "description": "วันที่ของรายงานบนหัวเอกสาร เช่น '6 มกราคม 2563'"
    },
    "price_date": {
      "type": "string",
      "description": "วันที่ปิดของราคาในตารางรายงาน เช่น '3 ม.ค. 63'"
    },
    "price_date_iso": {
      "type": "string",
      "description": "วันที่ปิดราคาน้ำมันแปลงเป็นรูปแบบ ISO YYYY-MM-DD เช่น '2020-01-03'"
    },
    "wti_price": {
      "type": "number",
      "description": "ราคาน้ำมันดิบเวสต์เท็กซัส (WTI) ต่อบาร์เรล (ตัวเลขทศนิยม)"
    },
    "wti_change": {
      "type": "number",
      "description": "ส่วนเปลี่ยนแปลงราคาน้ำมัน WTI (ตัวเลขทศนิยม มีเครื่องหมายลบหากลดลง)"
    },
    "brent_price": {
      "type": "number",
      "description": "ราคาน้ำมันดิบเบรนท์ (Brent) ต่อบาร์เรล (ตัวเลขทศนิยม)"
    },
    "brent_change": {
      "type": "number",
      "description": "ส่วนเปลี่ยนแปลงราคาน้ำมัน Brent (ตัวเลขทศนิยม มีเครื่องหมายลบหากลดลง)"
    },
    "dubai_price": {
      "type": "number",
      "description": "ราคาน้ำมันดิบดูไบ (Dubai) ต่อบาร์เรล (ตัวเลขทศนิยม)"
    },
    "dubai_change": {
      "type": "number",
      "description": "ส่วนเปลี่ยนแปลงราคาน้ำมันดูไบ (ตัวเลขทศนิยม มีเครื่องหมายลบหากลดลง)"
    },
    "factors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "direction": {
            "type": "string",
            "enum": ["+", "-", "+/-"],
            "description": "เครื่องหมายบอกประเภทปัจจัย (+ = ส่งผลบวก, - = ส่งผลลบ, +/- = ทิศทางกึ่งกลางหรือไม่แน่ชัด)"
          },
          "description": {
            "type": "string",
            "description": "รายละเอียดปัจจัยภาษาไทย"
          }
        },
        "required": ["direction", "description"]
      },
      "description": "รายการปัจจัยที่มีผลต่อราคาน้ำมัน"
    }
  },
  "required": [
    "report_date",
    "price_date",
    "price_date_iso",
    "wti_price",
    "wti_change",
    "brent_price",
    "brent_change",
    "dubai_price",
    "dubai_change",
    "factors"
  ]
}

def get_processed_files():
    """
    ตรวจสอบไฟล์ CSV เดิมเพื่อดึงรายชื่อไฟล์ที่เคยประมวลผลไปแล้ว
    ช่วยให้สามารถกดรันสคริปต์ต่อจากเดิมได้ทันทีหากโปรแกรมหยุดทำงานกลางคัน
    """
    processed = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("File_Name"):
                        processed.add(row["File_Name"])
        except Exception as e:
            print(f"⚠️ ไม่สามารถเปิดเช็คไฟล์เอาต์พุตเดิมได้ (อาจเพราะไฟล์ถูกเปิดอยู่): {e}")
    return processed

def write_headers_if_new():
    """สร้างหัวตาราง CSV หากยังไม่เคยมีไฟล์มาก่อน"""
    if not os.path.exists(OUTPUT_FILE):
        headers = [
            "File_Name", "Report_Date", "Price_Date", "Price_Date_ISO",
            "WTI_Price", "WTI_Change", "Brent_Price", "Brent_Change",
            "Dubai_Price", "Dubai_Change", "Factors_Summary", "Processed_At"
        ]
        with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def extract_pdf_data(file_path):
    """แปลง PDF เป็น base64 และส่งหา Gemini API เพื่อสกัดข้อมูล"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    
    with open(file_path, "rb") as f:
        pdf_data = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "contents": [{
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "application/pdf",
                        "data": pdf_data
                    }
                },
                {
                    "text": (
                        "วิเคราะห์ข้อมูลรายงานราคาน้ำมันดิบรายวันจากไฟล์ PDF นี้ "
                        "และสกัดราคา WTI, Brent, Dubai, ส่วนเปลี่ยนแปลง และข้อคิดเห็นปัจจัยสำคัญทั้งหมด"
                        "ให้ถูกต้องตามโครงสร้าง schema ที่กำหนดไว้อย่างเคร่งครัด"
                    )
                }
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": JSON_SCHEMA,
            "temperature": 0.1
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    
    if response.status_code == 200:
        res_json = response.json()
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_text.strip())
    elif response.status_code == 503:
        raise Exception("503 Service Unavailable (API กำลังหนาแน่นชั่วคราว)")
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

def main():
    if API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ ข้อผิดพลาด: กรุณาแก้ไขตัวแปร API_KEY ที่บรรทัด 9 ก่อนเริ่มทำงาน")
        return
        
    if not os.path.exists(INPUT_DIR):
        print(f"❌ ข้อผิดพลาด: ไม่พบโฟลเดอร์นำเข้าข้อมูลที่: {INPUT_DIR}")
        return

    # ค้นหาไฟล์ PDF ทั้งหมดในโฟลเดอร์ของปี 2020
    pdf_files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")])
    total_files = len(pdf_files)
    
    if total_files == 0:
        print(f"⚠️ ไม่พบไฟล์ PDF ในโฟลเดอร์ {INPUT_DIR}")
        return

    print(f"📂 ตรวจพบไฟล์ PDF ทั้งหมด {total_files} ไฟล์ในโฟลเดอร์ปี 2020")
    
    # ดึงรายชื่อไฟล์ที่เคยทำไปแล้วเพื่อสนับสนุนระบบเขียนข้อมูลต่อจากเดิม (Resume)
    processed_files = get_processed_files()
    if processed_files:
        print(f"⏩ ตรวจพบไฟล์ที่ทำเสร็จแล้วในระบบ {len(processed_files)} ไฟล์ (จะทำการรันไฟล์ส่วนที่เหลือต่อ)")
        
    write_headers_if_new()
    
    success_count = 0
    fail_count = 0
    
    for idx, filename in enumerate(pdf_files, 1):
        if filename in processed_files:
            continue
            
        file_path = os.path.join(INPUT_DIR, filename)
        print(f"\n🔄 [{idx}/{total_files}] กำลังประมวลผลไฟล์: {filename}...")
        
        retry_delay = 8.0 # เวลาหน่วงคิวปกติ
        max_retries = 3
        attempt = 0
        success = False
        
        while attempt < max_retries and not success:
            try:
                # ส่งไฟล์หา Gemini
                data = extract_pdf_data(file_path)
                
                # ฟอร์แมตปัจจัย (Factors) ให้อยู่ในฟอร์แมตข้อความเดียวคั่นด้วยการขึ้นบรรทัดใหม่
                factors_text = ""
                if "factors" in data and isinstance(data["factors"], list):
                    factors_text = "\n\n".join([
                        f"({item['direction']}) {item['description']}" 
                        for item in data["factors"] 
                        if "direction" in item and "description" in item
                    ])
                
                # เขียนแถวข้อมูลบันทึกลง CSV ทันทีเพื่อบันทึกประวัติการทำงานแบบ Real-time
                with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        filename,
                        data.get("report_date"),
                        data.get("price_date"),
                        data.get("price_date_iso"),
                        data.get("wti_price"),
                        data.get("wti_change"),
                        data.get("brent_price"),
                        data.get("brent_change"),
                        data.get("dubai_price"),
                        data.get("dubai_change"),
                        factors_text,
                        time.strftime("%Y-%m-%d %H:%M:%S")
                    ])
                
                print(f"✅ สกัดข้อมูลสำเร็จ: Date: {data.get('price_date_iso')} | WTI: {data.get('wti_price')} | Brent: {data.get('brent_price')} | Dubai: {data.get('dubai_price')}")
                success = True
                success_count += 1
                
            except Exception as e:
                attempt += 1
                print(f"⚠️ ข้อผิดพลาดในการสกัดข้อมูลรอบที่ {attempt}: {e}")
                if attempt < max_retries:
                    wait_time = 15.0  # รอ 15 วินาทีก่อนลองใหม่กรณีเจอ 503 หรือ Timeout
                    print(f"⏳ กำลังรอ {wait_time} วินาทีก่อนพยายามรันอีกครั้ง...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ ล้มเหลวโดยสิ้นเชิงหลังจากพยายามครบ {max_retries} ครั้ง ข้ามไฟล์นี้ไปไฟล์ถัดไป")
                    fail_count += 1
        
        # หน่วงเวลาหน่วงคิวปกติเพื่อให้อยู่ภายใต้โควต้า 15 RPM
        time.sleep(retry_delay)
        
    print(f"\n🎉 ดำเนินการเสร็จสิ้นที้งหมด!")
    print(f"📊 ผลการประมวลผลรอบนี้: สำเร็จ {success_count} ไฟล์ | ล้มเหลว {fail_count} ไฟล์")
    print(f"💾 ตารางผลลัพธ์ถูกบันทึกไว้ที่ไฟล์: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
