import os
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup

# 1. สร้างโฟลเดอร์สำหรับเก็บไฟล์ PDF
save_folder = "thaioil_reports"
if not os.path.exists(save_folder):
    os.makedirs(save_folder)

# 2. ตั้งค่าหน้าเริ่มต้นและหน้าสุดท้ายที่ต้องการโหลด
start_page = 1
end_page = 18  # ลองปรับเป็น 2 ก่อนเพื่อทดสอบ ถ้าเวิร์คค่อยเพิ่มเป็น 346

# 3. URL ของ API (Ajax Endpoint)
url = 'https://www.thaioilgroup.com/wp-admin/admin-ajax.php'

# 4. ตั้งค่า Headers ให้เหมือนเบราว์เซอร์เป๊ะๆ (สำคัญมาก ไม่งั้นอาจโดนบล็อก)
headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9,th;q=0.8',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://www.thaioilgroup.com',
    'referer': 'https://www.thaioilgroup.com/en/oil-prices-information/oil-prices-information-center-review/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest'
}

# 5. เตรียม Payload พื้นฐาน (แกะมาจาก data-raw)
# ตัด paged=2 ออกไปก่อน เพราะเราจะเอาไปใส่ใน Loop
raw_payload_base = "action=jet_smart_filters&provider=jet-engine%2Foil-publication-post&settings%5Blisitng_id%5D=38256&settings%5Bcolumns%5D=1&settings%5Bcolumns_tablet%5D=&settings%5Bcolumns_mobile%5D=&settings%5Bcolumn_min_width%5D=240&settings%5Bcolumn_min_width_tablet%5D=&settings%5Bcolumn_min_width_mobile%5D=&settings%5Binline_columns_css%5D=false&settings%5Bpost_status%5D%5B%5D=publish&settings%5Buse_random_posts_num%5D=&settings%5Bposts_num%5D=5&settings%5Bmax_posts_num%5D=9&settings%5Bnot_found_message%5D=%0A%0A%3Cimg+src%3D%22https%3A%2F%2Fthaioilwebsite.s3.ap-southeast-1.amazonaws.com%2Fwp-content%2Fuploads%2F2024%2F11%2F01152303%2FSearch-Not-Found-Image.png%22+alt%3D%22Trulli%22+width%3D%22100%22+height%3D%2250%22%3E%0A%3Cp%3ENo+Results+Found%3C%2Fp%3E%0A%0A&settings%5Bis_masonry%5D=&settings%5Bequal_columns_height%5D=&settings%5Buse_load_more%5D=&settings%5Bload_more_id%5D=&settings%5Bload_more_type%5D=click&settings%5Bload_more_offset%5D%5Bunit%5D=px&settings%5Bload_more_offset%5D%5Bsize%5D=0&settings%5Bloader_text%5D=&settings%5Bloader_spinner%5D=&settings%5Buse_custom_post_types%5D=&settings%5Bcustom_post_types%5D=&settings%5Bhide_widget_if%5D=&settings%5Bcarousel_enabled%5D=&settings%5Bslides_to_scroll%5D=1&settings%5Barrows%5D=true&settings%5Barrow_icon%5D=fa+fa-angle-left&settings%5Bdots%5D=&settings%5Bautoplay%5D=true&settings%5Bpause_on_hover%5D=true&settings%5Bautoplay_speed%5D=5000&settings%5Binfinite%5D=true&settings%5Bcenter_mode%5D=&settings%5Beffect%5D=slide&settings%5Bspeed%5D=500&settings%5Binject_alternative_items%5D=&settings%5Bscroll_slider_enabled%5D=&settings%5Bscroll_slider_on%5D%5B%5D=desktop&settings%5Bscroll_slider_on%5D%5B%5D=tablet&settings%5Bscroll_slider_on%5D%5B%5D=mobile&settings%5Bcustom_query%5D=&settings%5Bcustom_query_id%5D=&settings%5B_element_id%5D=oil-publication-post&settings%5Bcollapse_first_last_gap%5D=&settings%5Blist_items_wrapper_tag%5D=div&settings%5Blist_item_tag%5D=div&settings%5Bempty_items_wrapper_tag%5D=div&settings%5Blist_tags_selection%5D=&settings%5Bjet_cct_query%5D=%7B%22offset%22%3A%22%22%2C%22status%22%3A%22%22%2C%22order%22%3A%5B%7B%22orderby%22%3A%22cct_created%22%2C%22order%22%3A%22desc%22%2C%22type%22%3A%22auto%22%7D%5D%2C%22args%22%3A%5B%7B%22field%22%3A%22oil_publication_name_en%22%2C%22operator%22%3A%22%21%3D%22%2C%22value%22%3A%22%22%2C%22type%22%3A%22auto%22%7D%5D%7D&settings%5Bjet_rest_query%5D=&props%5Bfound_posts%5D=1730&props%5Bmax_num_pages%5D=346&props%5Bpage%5D=3&props%5Bquery_type%5D=custom-content-type&props%5Bquery_meta%5D%5Bcontent_type%5D=oil_publication"

print("เริ่มกระบวนการดาวน์โหลด...\n")

for page in range(start_page, end_page + 1):
    print(f"กำลังดึงข้อมูลหน้า {page}...")
    
    # เติมหมายเลขหน้าลงไปใน Payload
    payload = f"{raw_payload_base}&paged={page}"
    
    try:
        # ใช้ requests.post เพราะเป็นการส่งข้อมูลแบบ AJAX
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        # ข้อมูลที่ได้กลับมาจะเป็น JSON
        data = response.json()
        
        # ปลั๊กอินนี้มักจะส่ง HTML ซ่อนมาในคีย์ 'content' หรือ 'html'
        html_content = data.get('content', '') 
        
        if not html_content:
            print(f"  ❌ ไม่พบ HTML ในหน้า {page}")
            continue
            
        # ใช้ BeautifulSoup แกะลิงก์ PDF ออกจาก HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        pdf_count = 0
        for link in links:
            href = link['href']
            
            # กรองเฉพาะลิงก์ PDF
            if '.pdf' in href.lower():
                # จัดการลิงก์ให้เป็น URL เต็ม
                if href.startswith('//'):
                    href = 'https:' + href
                elif not href.startswith('http'):
                    href = 'https://www.thaioilgroup.com' + href
                
                # ตั้งชื่อไฟล์ (พยายามดึงจาก URL)
                file_name = urllib.parse.unquote(href.split('/')[-1])
                save_path = os.path.join(save_folder, file_name)
                
                if os.path.exists(save_path):
                    print(f"  [ข้าม] มีไฟล์ {file_name} อยู่แล้ว")
                    continue
                    
                print(f"  -> กำลังโหลด: {file_name}")
                
                # โหลดไฟล์ PDF
                pdf_response = requests.get(href, headers={'user-agent': headers['user-agent']})
                with open(save_path, 'wb') as f:
                    f.write(pdf_response.content)
                
                pdf_count += 1
                time.sleep(1) # พัก 1 วินาทีระหว่างโหลดไฟล์
                
        if pdf_count == 0:
            print(f"  ไม่มีไฟล์ PDF ให้ดาวน์โหลดในหน้า {page}")
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในหน้า {page}: {e}")
        
    # พักสักนิดก่อนเปลี่ยนหน้า
    time.sleep(2)

print("\n🎉 ดาวน์โหลดเสร็จสิ้น!")