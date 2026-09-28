import os
import shutil

# กำหนดโฟลเดอร์ต้นทางและปลายทาง
source_folder = "thaioil_reports"
weekly_folder = os.path.join(source_folder, "weekly_reports")

# สร้างโฟลเดอร์ปลายทางหากยังไม่มี
if not os.path.exists(weekly_folder):
    os.makedirs(weekly_folder)

# วนลูปตรวจสอบไฟล์ในโฟลเดอร์ต้นทาง
for filename in os.listdir(source_folder):
    if "Weekly" in filename and filename.endswith(".pdf"):
        # ย้ายไฟล์ที่มีคำว่า "Weekly" ไปยังโฟลเดอร์ปลายทาง
        source_path = os.path.join(source_folder, filename)
        destination_path = os.path.join(weekly_folder, filename)
        shutil.move(source_path, destination_path)
        print(f"ย้ายไฟล์ {filename} ไปยัง {weekly_folder}")

print("กระบวนการย้ายไฟล์เสร็จสิ้น!")