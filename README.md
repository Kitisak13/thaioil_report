# Thai Oil Daily Market Intelligence & Historical Price Database 🛢️

ระบบดาวน์โหลด สกัด และวิเคราะห์ข้อมูลรายงานสถานการณ์ราคาน้ำมันดิบรายวัน (Daily Oil Market Report) จากบริษัท ไทยออยล์ จำกัด (มหาชน) อัตโนมัติด้วย **Google Apps Script**, **Python** และ **Google Gemini Generative AI** พร้อมฐานข้อมูลราคาน้ำมันย้อนหลังตั้งแต่ปี 2020 - 2026 (รวมกว่า 1,440+ วันทำการ)

---

## 📂 โครงสร้างของโปรเจกต์ (Project Structure)

```text
├── google_apps_script.js         # สคริปต์ Google Apps Script สำหรับการดึงและสกัดข้อมูลรายวันแบบอัตโนมัติ
├── crude_oil_database.csv        # ฐานข้อมูลรวมราคาน้ำมันดิบและปัจจัย ย้อนหลัง 2020 - 2026 (1,441 แถว)
├── extract_2020.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2020
├── extract_2021.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2021
├── extract_2022.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2022
├── extract_2023.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2023
├── extract_2024.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2024
├── extract_2025.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2025
├── extract_2026.py               # สคริปต์ Python สำหรับสกัดข้อมูลย้อนหลังปี 2026
├── oil_prices_and_factors_*.csv  # ไฟล์ผลลัพธ์แยกตามรายปี (2020 - 2026)
├── scraping_oil.py               # สคริปต์ดาวน์โหลดไฟล์ PDF ต้นทางจากเว็บไซต์ไทยออยล์
├── .env.example                  # ตัวอย่างการตั้งค่าตัวแปรแวดล้อม (API Key)
└── .gitignore                    # ไฟล์ละเว้นที่ไม่นำขึ้น Git (PDF ดิบ, คีย์ลับ, แคช)
```

---

## 🚀 สถาปัตยกรรมระบบ (Architecture)

### 1. ระบบดึงข้อมูลอัตโนมัติประจำวัน (Daily Pipeline via Google Apps Script)
* ทำงานแบบ Serverless ไร้ค่าใช้จ่ายบนคลาวด์ของ Google
* ตั้งเวลาอัตโนมัติ (Time-driven Trigger) ตรวจสอบไฟล์รายงาน PDF ใหม่จากเว็บไซต์ไทยออยล์ทุกวัน
* บันทึกไฟล์สำรองเข้า **Google Drive**
* ส่งเนื้อหาเข้า **Gemini API** (`gemini-3.1-flash-lite`) เพื่ออ่านค่าราคาและสกัดสรุปปัจจัยตลาด (Market Sentiments) ตาม **Structured JSON Schema**
* บันทึกเข้า **Google Sheets** โดยอัตโนมัติ พร้อมระบบ **Self-healing Retry** (ตรวจสอบจากชีตโดยตรงเพื่อป้องกันข้อมูลตกหล่น)

### 2. ระบบสกัดและรวมฐานข้อมูลประวัติย้อนหลัง (Historical Extraction via Python)
* สคริปต์ Python รันผ่านเครื่องคอมพิวเตอร์ ทำการวนลูปสกัดข้อมูลจากไฟล์ PDF ย้อนหลัง 7 ปี (2020 - 2026)
* ควบคุมอัตราการส่งคำขอให้อยู่ภายใต้ Free Tier Limit ของ Google AI Studio (15 RPM)
* มีระบบ **Resume** ข้ามไฟล์ที่เคยประมวลผลสำเร็จแล้ว เพื่อให้กดรันต่อจากเดิมได้ทันทีหากหยุดชะงัก
* แปลงและปรับปรุงรูปแบบวันที่ให้เป็นมาตรฐานสากล **ISO 8601 (`YYYY-MM-DD`)** พร้อมเรียงลำดับเวลา (Chronological order)

---

## 📊 รายละเอียดฟิลด์ข้อมูลในฐานข้อมูล (Data Dictionary)

ไฟล์ `crude_oil_database.csv` ประกอบด้วยคอลัมน์สำคัญดังนี้:

| คอลัมน์ | รายละเอียด | ตัวอย่าง |
| :--- | :--- | :--- |
| `File_Name` | ชื่อไฟล์รายงาน PDF ต้นทาง | `Daily_Oil_TH_2026.09.24.pdf` |
| `Report_Date` | วันที่ระบุบนหัวเอกสาร | `24 กันยายน 2569` |
| `Price_Date` | วันที่ของราคาปิดตลาดตามตาราง | `23 ก.ย. 69` |
| `Price_Date_ISO` | วันที่ราคาปิดในรูปแบบมาตรฐาน (YYYY-MM-DD) | `2026-09-23` |
| `WTI_Price` | ราคาน้ำมันดิบเวสต์เท็กซัส (USD/BBL) | `70.38` |
| `WTI_Change` | การเปลี่ยนแปลงของราคา WTI | `-1.27` |
| `Brent_Price` | ราคาน้ำมันดิบเบรนท์ (USD/BBL) | `75.89` |
| `Brent_Change` | การเปลี่ยนแปลงของราคา Brent | `-1.15` |
| `Dubai_Price` | ราคาน้ำมันดิบดูไบ (USD/BBL) *(หมายเหตุ: ไทยออยล์ยกเลิกการแสดงในปี 2026)* | `77.98` / `0.0` |
| `Dubai_Change` | การเปลี่ยนแปลงของราคา Dubai | `+1.04` / `0.0` |
| `Factors_Summary` | สรุปปัจจัยที่มีผลกระทบต่อราคา พร้อมทิศทาง (+, -, +/-) | `(+) ความตึงเครียดในตะวันออกกลาง...` |
| `Processed_At` | วันและเวลาที่ระบบทำการสกัดข้อมูล | `2026-09-28 09:22:00` |

---

## 🛠️ การติดตั้งและใช้งาน (Setup & Usage)

### การใช้งาน Python Scripts:
1. ติดตั้งไลบรารีที่จำเป็น:
   ```bash
   pip install requests pdfplumber pandas
   ```
2. สร้างไฟล์ `.env` สำหรับเก็บคีย์ API (คัดลอกจาก `.env.example`):
   ```bash
   cp .env.example .env
   ```
   จากนั้นแก้ไขค่า `GEMINI_API_KEY` ด้วยคีย์ที่ได้จาก [Google AI Studio](https://aistudio.google.com/)
3. สั่งรันสคริปต์สกัดข้อมูลตามปีที่ต้องการ:
   ```bash
   python extract_2026.py
   ```

### การตั้งค่า Google Apps Script:
1. นำโค้ดจาก `google_apps_script.js` ไปวางในโปรเจกต์ Google Apps Script
2. ไปที่ **Project Settings (⚙️) > Script Properties** แล้วตั้งค่าดังนี้:
   * `GEMINI_API_KEY`: คีย์ Gemini API จาก Google AI Studio
   * `GEMINI_MODEL_NAME`: `gemini-3.1-flash-lite`
   * `DRIVE_FOLDER_ID`: รหัส ID โฟลเดอร์ใน Google Drive สำหรับเก็บ PDF
   * `SPREADSHEET_ID`: รหัส ID ของ Google Sheet
   * `DAILY_SHEET_NAME`: `Daily Reports`
3. ตั้งเวลาในเมนู **Triggers ⏰** ให้รันฟังก์ชัน `runOilReportPipeline` ทุกวันตามเวลาที่ต้องการ

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
