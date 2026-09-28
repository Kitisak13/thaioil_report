/**
 * ============================================================================
 * ระบบสกัดข้อมูลรายงานราคาน้ำมันไทยออยล์รายวันลง Google Sheets
 * เวอร์ชันปรับปรุง: ตรวจสอบความสมบูรณ์จาก Google Sheet โดยตรง (Self-healing Retry)
 * ป้องกันปัญหาไฟล์ค้างใน Drive แต่ข้อมูลไม่ลง Sheet
 * ============================================================================
 */

function runOilReportPipeline() {
  Logger.log("เริ่มกระบวนการดึงรายงานไทยออยล์...");
  
  var config = getSystemConfig();
  var ss = SpreadsheetApp.openById(config.spreadsheetId);
  var sheet = getOrCreateDailySheet(ss, config.dailySheetName);
  
  // 1. ดึงลิงก์ PDF ล่าสุดจากเว็บ Thai Oil (หน้า 1)
  var latestPdfs = fetchLatestPdfUrls();
  if (latestPdfs.length === 0) {
    Logger.log("❌ ไม่พบลิงก์ PDF บนเว็บไซต์");
    return;
  }
  
  var folder = DriveApp.getFolderById(config.driveFolderId);
  var processedCount = 0;
  
  for (var i = 0; i < latestPdfs.length; i++) {
    var pdfUrl = latestPdfs[i];
    var fileName = decodeURIComponent(pdfUrl.split('/').pop());
    var isWeekly = fileName.toLowerCase().indexOf("weekly") !== -1;
    
    // ตรวจสอบสถานะการประมวลผล
    if (isWeekly) {
      // สำหรับ Weekly: เช็คว่ามีไฟล์ใน Google Drive หรือยัง
      if (isFileInDrive(folder, fileName)) {
        Logger.log("⏩ ข้ามไฟล์ [Weekly] (มีใน Drive แล้ว): " + fileName);
        continue;
      }
    } else {
      // สำหรับ Daily: เช็คว่าถูกบันทึกลงใน Google Sheet แล้วหรือยัง (ป้องกันปัญหา AI หลุดแล้วไม่บันทึก)
      if (isFileAlreadyInSheet(sheet, fileName)) {
        Logger.log("⏩ ข้ามไฟล์ [Daily] (บันทึกลง Sheet เรียบร้อยแล้ว): " + fileName);
        continue;
      }
    }
    
    // ดึงไฟล์ PDF: ถ้ามีใน Drive แล้วให้นำมาใช้เลย ถ้ายังไม่มีให้ดาวน์โหลดใหม่
    var pdfFile = getFileFromDrive(folder, fileName);
    var pdfBlob = null;
    
    if (pdfFile) {
      Logger.log("📂 พบไฟล์เดิมใน Google Drive: " + fileName);
      pdfBlob = pdfFile.getBlob();
    } else {
      Logger.log("📥 กำลังดาวน์โหลดและบันทึกไฟล์ใหม่: " + fileName);
      pdfBlob = downloadFile(pdfUrl, fileName);
      pdfFile = folder.createFile(pdfBlob);
      Logger.log("✅ บันทึกลง Drive สำเร็จ (ID: " + pdfFile.getId() + ")");
    }
    
    // แยกการทำงานตามประเภทรายงาน
    if (isWeekly) {
      Logger.log("ℹ️ รายงาน [Weekly] -> บันทึกลง Drive เรียบร้อย (ข้ามขั้นตอนสกัดข้อมูล)");
      processedCount++;
    } else {
      Logger.log("🧠 รายงาน [Daily] -> กำลังวิเคราะห์และสกัดข้อมูลด้วย Gemini API...");
      var extractedData = extractDataWithGemini(pdfBlob, config);
      
      if (extractedData) {
        extractedData.fileName = fileName;
        extractedData.fileUrl = pdfFile.getUrl();
        
        // บันทึกข้อมูลลง Google Sheet
        saveRowToSheet(sheet, extractedData);
        processedCount++;
      } else {
        Logger.log("⚠️ สกัดข้อมูลไม่สำเร็จสำหรับไฟล์: " + fileName + " (จะทำการลองใหม่ในรอบถัดไป)");
      }
    }
    
    // พักการทำงานป้องกันปัญหา Rate limit
    Utilities.sleep(2000);
  }
  
  Logger.log("🎉 ดำเนินการเสร็จสิ้น! ทำงานสำเร็จทั้งหมด " + processedCount + " ไฟล์");
}

/**
 * ดึงค่าคุณสมบัติระบบจาก Script Properties พร้อมเคลียร์ช่องว่าง (Trim)
 */
function getSystemConfig() {
  var props = PropertiesService.getScriptProperties();
  
  var config = {
    apiKey: props.getProperty('GEMINI_API_KEY'),
    modelName: props.getProperty('GEMINI_MODEL_NAME'),
    driveFolderId: props.getProperty('DRIVE_FOLDER_ID'),
    spreadsheetId: props.getProperty('SPREADSHEET_ID'),
    dailySheetName: props.getProperty('DAILY_SHEET_NAME')
  };
  
  if (config.apiKey) config.apiKey = config.apiKey.trim();
  if (config.modelName) config.modelName = config.modelName.trim();
  if (config.driveFolderId) config.driveFolderId = config.driveFolderId.trim();
  if (config.spreadsheetId) config.spreadsheetId = config.spreadsheetId.trim();
  if (config.dailySheetName) config.dailySheetName = config.dailySheetName.trim();
  
  if (!config.modelName) config.modelName = 'gemini-3.1-flash-lite';
  if (!config.dailySheetName) config.dailySheetName = 'Daily Reports';
  
  if (!config.apiKey) {
    throw new Error("❌ กรุณาตั้งค่า Script Property: 'GEMINI_API_KEY' ก่อนรันระบบ");
  }
  if (!config.driveFolderId) {
    throw new Error("❌ กรุณาตั้งค่า Script Property: 'DRIVE_FOLDER_ID' ก่อนรันระบบ");
  }
  if (!config.spreadsheetId) {
    throw new Error("❌ กรุณาตั้งค่า Script Property: 'SPREADSHEET_ID' ก่อนรันระบบ");
  }
  
  return config;
}

/**
 * ตรวจสอบว่าไฟล์เคยถูกบันทึกลงใน Google Sheet (คอลัมน์ A) แล้วหรือยัง
 */
function isFileAlreadyInSheet(sheet, fileName) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return false;
  
  // อ่านเฉพาะคอลัมน์ A ตั้งแต่แถวที่ 2 ถึงแถวสุดท้าย
  var values = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
  for (var i = 0; i < values.length; i++) {
    if (values[i][0] === fileName) {
      return true;
    }
  }
  return false;
}

/**
 * ตรวจสอบว่ามีไฟล์ใน Google Drive หรือไม่
 */
function isFileInDrive(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  return files.hasNext();
}

/**
 * ดึงอ็อบเจกต์ File จาก Google Drive หากมีอยู่แล้ว
 */
function getFileFromDrive(folder, fileName) {
  var files = folder.getFilesByName(fileName);
  if (files.hasNext()) {
    return files.next();
  }
  return null;
}

/**
 * ดึงลิงก์ PDF ล่าสุดจาก AJAX API ของ Thai Oil (หน้า 1)
 */
function fetchLatestPdfUrls() {
  var url = 'https://www.thaioilgroup.com/wp-admin/admin-ajax.php';
  // แนะนำ posts_num = 10 เพื่อรองรับกรณีหยุดยาวหลายวัน
  var payload = 'action=jet_smart_filters&provider=jet-engine%2Foil-publication-post&settings%5Blisitng_id%5D=38256&settings%5Bcolumns%5D=1&settings%5Bposts_num%5D=10&props%5Bpage%5D=1&paged=1';
  
  var options = {
    method: 'post',
    contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
    payload: payload,
    muteHttpExceptions: true,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
  };
  
  try {
    var response = UrlFetchApp.fetch(url, options);
    var json = JSON.parse(response.getContentText());
    var htmlContent = json.content || '';
    
    var regex = /href=["']([^"']+\.pdf)/gi;
    var pdfUrls = [];
    var match;
    
    while ((match = regex.exec(htmlContent)) !== null) {
      var pdfUrl = match[1];
      if (pdfUrl.startsWith('//')) {
        pdfUrl = 'https:' + pdfUrl;
      } else if (!pdfUrl.startsWith('http')) {
        pdfUrl = 'https://www.thaioilgroup.com' + (pdfUrl.startsWith('/') ? '' : '/') + pdfUrl;
      }
      
      if (pdfUrls.indexOf(pdfUrl) === -1) {
        pdfUrls.push(pdfUrl);
      }
    }
    
    return pdfUrls;
  } catch (e) {
    Logger.log("❌ ขอข้อมูลจากเว็บล้มเหลว: " + e.toString());
    return [];
  }
}

/**
 * ดาวน์โหลดไฟล์ PDF เป็น Blob
 */
function downloadFile(url, fileName) {
  var options = {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
  };
  var response = UrlFetchApp.fetch(url, options);
  return response.getBlob().setName(fileName);
}

/**
 * ส่งไฟล์ PDF รายวันไปสกัดข้อมูลผ่าน Gemini API
 */
function extractDataWithGemini(pdfBlob, config) {
  var base64Data = Utilities.base64Encode(pdfBlob.getBytes());
  var apiUrl = 'https://generativelanguage.googleapis.com/v1beta/models/' + config.modelName + ':generateContent?key=' + config.apiKey;
  
  var jsonSchema = {
    type: "object",
    properties: {
      report_date: {
        type: "string",
        description: "วันที่ที่ปรากฏบนหัวรายงาน เช่น '24 กันยายน 2569'"
      },
      price_date: {
        type: "string",
        description: "วันที่ของราคาน้ำมันดิบที่ปิดทำการล่าสุด เช่น '23 ก.ย. 69'"
      },
      price_date_iso: {
        type: "string",
        description: "วันที่ของราคาน้ำมันปิด ทำการแปลงให้อยู่ในรูปแบบ ISO YYYY-MM-DD เช่น '2026-09-23'"
      },
      wti_price: {
        type: "number",
        description: "ราคาน้ำมันดิบเวสต์เท็กซัส (WTI) ต่อบาร์เรล (ตัวเลขทศนิยม)"
      },
      wti_change: {
        type: "number",
        description: "ส่วนเปลี่ยนแปลงราคาน้ำมัน WTI (มีเครื่องหมายติดลบหากราคาลดลง เช่น -1.44)"
      },
      brent_price: {
        type: "number",
        description: "ราคาน้ำมันดิบเบรนท์ (Brent) ต่อบาร์เรล (ตัวเลขทศนิยม)"
      },
      brent_change: {
        type: "number",
        description: "ส่วนเปลี่ยนแปลงราคาน้ำมัน Brent (มีเครื่องหมายติดลบหากราคาลดลง เช่น -1.72)"
      },
      dubai_price: {
        type: "number",
        description: "ราคาน้ำมันดิบดูไบ (Dubai) ต่อบาร์เรล (ตัวเลขทศนิยม) หากไม่มีระบุในรายงานให้ส่งค่าเป็น null"
      },
      dubai_change: {
        type: "number",
        description: "ส่วนเปลี่ยนแปลงราคาน้ำมันดิบดูไบ (ตัวเลขทศนิยม) หากไม่มีระบุในรายงานให้ส่งค่าเป็น null"
      },
      factors: {
        type: "array",
        items: {
          type: "object",
          properties: {
            direction: {
              type: "string",
              enum: ["+", "-", "+/-"],
              description: "เครื่องหมายบอกผลกระทบ (+ = เป็นบวก, - = เป็นลบ, +/- = มีทั้งสองอย่างหรือแนวโน้มไม่แน่ชัด)"
            },
            description: {
              type: "string",
              description: "สรุปรายละเอียดปัจจัยที่มีผลต่อราคาน้ำมันในข้อนี้นั้นๆ เป็นภาษาไทย"
            }
          },
          required: ["direction", "description"]
        },
        description: "สรุปข้อมูลปัจจัยทั้งหมดที่มีผลกระทบต่อราคาน้ำมันจากรายงาน"
      }
    },
    required: [
      "report_date",
      "price_date",
      "price_date_iso",
      "wti_price",
      "wti_change",
      "brent_price",
      "brent_change",
      "factors"
    ]
  };

  var prompt = "วิเคราะห์ข้อมูลรายงานราคาน้ำมันดิบรายวันจากไฟล์ PDF นี้ และสกัดราคา WTI, Brent, Dubai (หากมี), ส่วนเปลี่ยนแปลง และข้อคิดเห็นปัจจัยสำคัญทั้งหมดให้ถูกต้องตามโครงสร้าง schema ที่กำหนดไว้อย่างเคร่งครัด";

  var requestBody = {
    contents: [{
      parts: [
        {
          inlineData: {
            mimeType: "application/pdf",
            data: base64Data
          }
        },
        {
          text: prompt
        }
      ]
    }],
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: jsonSchema,
      temperature: 0.1
    }
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(apiUrl, options);
    var responseCode = response.getResponseCode();
    var responseText = response.getContentText();
    
    if (responseCode !== 200) {
      Logger.log("❌ เรียกใช้งาน Gemini API ล้มเหลว: Code " + responseCode + " - " + responseText);
      return null;
    }
    
    var responseJson = JSON.parse(responseText);
    var candidateText = responseJson.candidates[0].content.parts[0].text;
    
    var extractedJson = JSON.parse(candidateText.trim());
    Logger.log("✅ สกัดข้อมูลจาก Gemini API สำเร็จ!");
    return extractedJson;
    
  } catch (e) {
    Logger.log("❌ เกิดข้อผิดพลาดในการวิเคราะห์ข้อมูล: " + e.toString());
    return null;
  }
}

/**
 * ดึงแผ่นงาน Daily หรือสร้างใหม่พร้อมหัวตารางหากยังไม่มี
 */
function getOrCreateDailySheet(ss, sheetName) {
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    Logger.log("⚠️ ไม่พบชีต [" + sheetName + "] กำลังสร้างชีตใหม่...");
    sheet = ss.insertSheet(sheetName);
    sheet.appendRow([
      "File Name", 
      "Report Date", 
      "Price Date", 
      "Price Date (ISO)", 
      "WTI Price", 
      "WTI Change", 
      "Brent Price", 
      "Brent Change", 
      "Dubai Price", 
      "Dubai Change", 
      "Factors Summary", 
      "File URL", 
      "Processed At"
    ]);
  }
  return sheet;
}

/**
 * บันทึกข้อมูลแถวใหม่ลงใน Google Sheet
 */
function saveRowToSheet(sheet, data) {
  var factorsText = "";
  if (data.factors && data.factors.length > 0) {
    factorsText = data.factors.map(function(item) {
      return "(" + item.direction + ") " + item.description;
    }).join("\n\n");
  }
  
  sheet.appendRow([
    data.fileName,
    data.report_date,
    data.price_date,
    data.price_date_iso,
    data.wti_price,
    data.wti_change,
    data.brent_price,
    data.brent_change,
    data.dubai_price,
    data.dubai_change,
    factorsText,
    data.fileUrl,
    new Date()
  ]);
  
  Logger.log("💾 บันทึกข้อมูลลง Sheet เรียบร้อย: " + data.fileName + " (Date: " + data.price_date_iso + ")");
}

/**
 * ทดสอบการเชื่อมต่อ
 */
function testConnection() {
  Logger.log("--- เริ่มตรวจสอบสิทธิ์ตัวแปรและการเชื่อมต่อเว็บบอร์ด ---");
  try {
    var config = getSystemConfig();
    Logger.log("✅ การตั้งค่าระบบถูกต้อง:");
    Logger.log("  - Model Name: " + config.modelName);
    Logger.log("  - Drive Folder ID: " + config.driveFolderId);
    Logger.log("  - Spreadsheet ID: " + config.spreadsheetId);
    Logger.log("  - Sheet Name: " + config.dailySheetName);
    
    Logger.log("🌐 กำลังทดสอบดึง URL เอกสารจากเว็บบอร์ด...");
    var urls = fetchLatestPdfUrls();
    Logger.log("✅ ค้นพบไฟล์เอกสารทั้งสิ้น: " + urls.length + " ไฟล์");
    for (var i = 0; i < urls.length; i++) {
      Logger.log("  [" + (i+1) + "] " + urls[i]);
    }
  } catch (e) {
    Logger.log("❌ พบข้อผิดพลาดในการตรวจสอบ: " + e.toString());
  }
  Logger.log("-----------------------------------------");
}
