import os
import pdfplumber
import pandas as pd
import re

pdf_folder = "thaioil_reports"
extracted_data = []

print(f"กำลังเริ่มสแกนไฟล์ในโฟลเดอร์: {pdf_folder}...\n")

pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]

# ดึงข้อมูลราคา
for filename in pdf_files:
    file_path = os.path.join(pdf_folder, filename)
    
    data_row = {
        "File_Name": filename,
        "Date": None,
        "WTI": None,
        "Brent": None,
        "Factors": ""
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            first_page = pdf.pages[0]
            
            # ดึงข้อความทั้งหมดในหน้าแรกออกมาเป็น Text ดิบๆ
            text = first_page.extract_text()
            
            if text:
                lines = text.split('\n')
                capturing_factors = False
                factors_list = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # --- 1. ค้นหา วันที่ ---
                    if "เหรียญสหรัฐ" in line and "ต่อบาร์เรล" in line:
                        # ดึงข้อความที่อยู่ระหว่างคำว่า "ต่อบาร์เรล" และ "เปลี่ยนแปลง"
                        match_date = re.search(r'ต่อบาร์เรล(.*?)(เปลี่ยนแปลง|$)', line)
                        if match_date:
                            data_row["Date"] = match_date.group(1).strip()
                            
                    # --- 2. ค้นหา ราคาน้ำมัน (ใช้ Regex จับตัวเลขทศนิยมที่อยู่หลังชื่อ) ---
                    if "เวสต์เท็กซัส" in line:
                        match_wti = re.search(r'เวสต์เท็กซัส.*?(\d+\.\d+)', line)
                        if match_wti:
                            data_row["WTI"] = match_wti.group(1)
                            
                    if "เบรนท์" in line:
                        match_brent = re.search(r'เบรนท์.*?(\d+\.\d+)', line)
                        if match_brent:
                            data_row["Brent"] = match_brent.group(1)

                    # --- 3. ค้นหา ปัจจัยที่ส่งผลกระทบ ---
                    if "ปัจจัยที่ส่งผลกระทบ" in line:
                        capturing_factors = True
                        continue 
                        
                    # ดักจับกรณีที่ไม่มีหัวข้อ แต่ขึ้นต้นด้วย (+) หรือ (-) เลย
                    elif not capturing_factors and (line.startswith('(+)') or line.startswith('(-)') or line.startswith('+ ') or line.startswith('- ')):
                        capturing_factors = True
                    
                    if capturing_factors:
                        # หยุดเก็บเมื่อเจอหัวข้อถัดไป
                        if "ราคาน้ำมันเบนซิน" in line or "ราคาน้ำมันดีเซล" in line or "Thai Oil" in line or "หน่วยวิเคราะห์" in line or "ราคา" in line and "สำเร็จรูป" in line:
                            capturing_factors = False
                        else:
                            factors_list.append(line)
                
                # รวมข้อความปัจจัยเข้าด้วยกัน
                data_row["Factors"] = " ".join(factors_list).strip()

        extracted_data.append(data_row)
        print(f"✅ สกัดสำเร็จ: {filename} | Date: {data_row['Date']} | WTI: {data_row['WTI']} | Brent: {data_row['Brent']}")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดกับไฟล์ {filename}: {e}")

# บันทึกเป็น CSV
if extracted_data:
    df = pd.DataFrame(extracted_data)
    df = df[['File_Name', 'Date', 'WTI', 'Brent', 'Factors']]
    
    output_file = "oil_prices_and_factors.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n🎉 สกัดข้อมูลเสร็จสิ้น! บันทึกผลลัพธ์ลงไฟล์ {output_file} เรียบร้อยแล้ว")
else:
    print("\n⚠️ ไม่พบข้อมูลราคาน้ำมัน โปรดตรวจสอบ")