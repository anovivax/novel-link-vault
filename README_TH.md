# Novel ID Vault V3 — Modern 2D Logo Edition

เวอร์ชันนี้เพิ่ม **โลโก้ 2D สไตล์โมเดิร์น** และนำไปใส่ในโปรเจคเรียบร้อยแล้ว ทั้งในส่วนหัวเว็บ, หน้าเปิดโลโก้ (splash screen) และไอคอนสำหรับปักหน้าเว็บบนมือถือ

## ไฟล์สำคัญในชุดนี้

| ไฟล์ | หน้าที่ |
| --- | --- |
| `index.html` | หน้าเว็บหลักของระบบ |
| `book_ids.json` | เก็บ Book ID และสถานะ `copied_ids` |
| `logo-2d.png` | โลโก้หลักแบบ 2D Modern |
| `favicon-64.png` | ไอคอนแท็บเบราว์เซอร์ |
| `apple-touch-icon.png` | ไอคอนสำหรับ iPhone / iPad |
| `icon-192.png` | ไอคอน Android / PWA |
| `icon-512.png` | ไอคอนขนาดใหญ่สำหรับติดตั้งเว็บแอป |
| `manifest.webmanifest` | ข้อมูลเว็บแอปสำหรับมือถือ |
| `sync_windows.py` | ซิงก์ GitHub ↔ Windows |
| `start_sync_windows.bat` | เปิดตัวซิงก์บน Windows แบบง่าย |

---

# วิธีใช้งานใหม่ทั้งหมด

## 1) เตรียม GitHub Repository

1. เข้า GitHub แล้วสร้าง Repository ใหม่ เช่น `novel-link-vault`
2. ให้อัปโหลดไฟล์เหล่านี้ขึ้นไปที่ root ของ repo:
   - `index.html`
   - `book_ids.json`
   - `logo-2d.png`
   - `favicon-64.png`
   - `apple-touch-icon.png`
   - `icon-192.png`
   - `icon-512.png`
   - `manifest.webmanifest`
3. กด Commit ให้เรียบร้อย

> ถ้าลืมอัปโหลดไฟล์โลโก้ เว็บยังเปิดได้ แต่โลโก้, splash screen และไอคอนมือถือจะไม่สมบูรณ์

## 2) เปิด GitHub Pages

1. เข้า repo ของคุณ
2. ไปที่ **Settings → Pages**
3. เลือก **Deploy from a branch**
4. เลือก branch `main` และ folder `/ (root)`
5. กด Save
6. รอสักครู่ จะได้ลิงก์เว็บ เช่น  
   `https://USERNAME.github.io/novel-link-vault/`

## 3) สร้าง GitHub Token

1. เข้าเมนูสร้าง **Fine-grained personal access token**
2. เลือกเฉพาะ repo นี้
3. ให้สิทธิ์ **Contents: Read and write**
4. สร้าง token แล้วคัดลอกเก็บไว้

> ห้ามเอา token ไปใส่ในโค้ด HTML หรือ commit ขึ้น GitHub

## 4) เปิดเว็บครั้งแรก

เมื่อเปิดเว็บครั้งแรก จะมี **หน้าโลโก้ (splash screen)** ขึ้นมาอัตโนมัติ แล้วจึงเข้าสู่หน้าหลัก

ในหน้าหลัก:
1. กดปุ่ม **ตั้งค่า**
2. กรอก
   - GitHub Owner
   - Repository
   - Branch (เช่น `main`)
   - Token
3. กด **เชื่อมต่อและโหลดข้อมูล**

เมื่อเชื่อมต่อสำเร็จ ระบบจะโหลด Book ID จาก `book_ids.json`

## 5) วิธีเพิ่มลิงก์นิยาย

คุณสามารถวางได้ทั้ง:
- ลิงก์ Fanqie เช่น `https://fanqienovel.com/page/7132121215128308767`
- ลิงก์ Changdu ที่มี `book_id=...`
- หรือวางตัวเลข Book ID ตรง ๆ

ขั้นตอน:
1. วางลิงก์ลงในช่อง **เพิ่มลิงก์นิยาย**
2. ระบบจะสกัด `book_id` ให้อัตโนมัติ
3. ถ้ามี ID ซ้ำ ระบบจะไม่บันทึกซ้ำ
4. กด **บันทึกลง GitHub**

## 6) วิธีคัดลอก Book ID

ในหน้า **คลัง Book ID**:
- กดที่ตัวเลข `Book ID` เพื่อคัดลอกได้ทันที
- เมื่อคัดลอกสำเร็จ ระบบจะทำเครื่องหมายว่า **คัดลอกแล้ว** ให้อัตโนมัติ
- ปุ่มด้านขวาใช้กดทำเครื่องหมายเองได้ แม้ยังไม่ได้กดคัดลอกจากหน้าเว็บ

นอกจากนี้ยังมี:
- ตัวกรอง **ทั้งหมด / ยังไม่คัดลอก / คัดลอกแล้ว**
- ปุ่ม **คัดลอกทั้งหมด**
- ช่องค้นหา Book ID

## 7) วิธีใช้งานบนมือถือและปักหน้า Home Screen

### Android (Chrome)
1. เปิดเว็บ GitHub Pages ของคุณใน Chrome
2. กดเมนู `⋮`
3. เลือก **Add to Home screen** หรือ **Install app**
4. โลโก้ที่ขึ้นบนหน้าจอมือถือจะใช้ไฟล์จาก `manifest.webmanifest` และ `icon-192.png` / `icon-512.png`

### iPhone / iPad (Safari)
1. เปิดเว็บใน Safari
2. กดปุ่ม Share
3. เลือก **Add to Home Screen**
4. ระบบจะใช้ `apple-touch-icon.png`

## 8) ซิงก์ข้อมูลลง Windows ที่ D:\[ NOVEL ]\History

1. ติดตั้ง Python 3.9 ขึ้นไป
2. แตกไฟล์ ZIP ไว้ในคอม เช่น `D:\NovelIDVault`
3. ดับเบิลคลิก `start_sync_windows.bat`
4. กรอก owner / repo / branch / token
5. โปรแกรมจะซิงก์ข้อมูลจาก GitHub ไปที่  
   `D:\[ NOVEL ]\History\book_ids.json`

ระบบจะเช็กข้อมูลซ้ำและรวมข้อมูลให้โดยไม่ซ้ำ

## 9) อัปเดตจากเวอร์ชันเก่า

ถ้าคุณมีโปรเจคเดิมอยู่แล้ว ให้แทนที่ไฟล์ต่อไปนี้:
- `index.html`
- `sync_windows.py`
- `logo-2d.png`
- `favicon-64.png`
- `apple-touch-icon.png`
- `icon-192.png`
- `icon-512.png`
- `manifest.webmanifest`

**อย่านำ `book_ids.json` ตัวอย่างไปทับไฟล์จริงบน GitHub ถ้ามีข้อมูลใหม่อยู่แล้ว**

## 10) หมายเหตุสำคัญ

- หน้าโลโก้จะแสดงอัตโนมัติทุกครั้งที่เปิดเว็บ และจะหายไปเอง
- ถ้าแตะหน้าจอระหว่างหน้าโลโก้ ก็จะข้ามเข้าเว็บได้ทันที
- โลโก้ใหม่เป็นงาน 2D แบบโมเดิร์น ใช้ได้ทั้งหัวเว็บ, หน้าเปิด และไอคอนมือถือ
- ถ้า repo เป็น Public รายการ Book ID จะถูกมองเห็นได้สาธารณะ

---

## สรุปสั้น ๆ

ถ้าจะใช้งานแบบเร็วที่สุด ให้ทำตามนี้:
1. อัปโหลดไฟล์ทั้งหมดขึ้น GitHub
2. เปิด GitHub Pages
3. สร้าง Token
4. เปิดเว็บ → ตั้งค่า GitHub
5. วางลิงก์ → บันทึก → กด Book ID เพื่อคัดลอก
6. ถ้าต้องการไฟล์ลงไดรฟ์ D: ให้เปิด `start_sync_windows.bat`
