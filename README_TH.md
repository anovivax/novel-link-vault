# Novel ID Vault V4 — แชร์ลิงก์ครั้งเดียว ใช้ได้ทุกเครื่อง

## สิ่งที่เปลี่ยนจาก V3

- **ไม่ต้องกรอก GitHub Token บนมือถือ/คอมเครื่องใหม่อีกต่อไป**
- เก็บ GitHub Token เป็น **Secret ฝั่ง Cloudflare Worker** แทนหน้าเว็บ
- กด **แชร์ลิงก์** ในหน้าเว็บเพื่อคัดลอก URL ส่วนตัว เช่น `https://my-novel-vault.example.workers.dev/#access=รหัสยาวๆ`
- ผู้รับเปิด URL ดังกล่าวแล้วใช้งานคลังเดียวกันได้เลย ไม่ต้องใส่ Token หรือตั้งค่า Repo ซ้ำ
- ยังรองรับ Fanqie / Changdu, ID ไม่ซ้ำ, คัดลอกแล้ว, โลโก้ 2D, Splash Screen, ไอคอนหน้าจอมือถือ, ซิงก์ JSON Windows

> **คำเตือนเรื่องสิทธิ์:** URL ที่มี `#access=...` เปรียบเหมือนกุญแจเข้าใช้คลัง ผู้ได้ลิงก์สามารถอ่านและแก้ไข Book ID ได้ทั้งหมด **ห้ามโพสต์ลิงก์สาธารณะ** ถ้าหลุด ให้เปลี่ยน `VAULT_ACCESS_KEY` ใน Cloudflare Worker และแชร์ลิงก์ใหม่ ผู้ถือกุญแจเดิมจะเข้าไม่ได้

## โครงสร้าง

มือถือ / คอม → **Cloudflare Worker (ลิงก์เดียว)** → GitHub API → `book_ids.json`

- ส่วนเว็บบน Worker ดึงหน้า `index.html` และรูปจาก GitHub Pages ที่คุณเผยแพร่อยู่
- API `/api/health` ตรวจ Repo / Branch / ไฟล์ และแยกข้อผิดพลาด 404 อย่างละเอียด
- API `/api/books` ใช้อ่าน เพิ่ม ID และทำเครื่องหมายโดยตรวจข้อมูลซ้ำและลองเขียนใหม่หากเกิดการแก้ไขพร้อมกัน
- Cloudflare Worker ถือ GitHub Token ไว้ฝั่งเซิร์ฟเวอร์เท่านั้น
- ตัวซิงก์ Windows ของ V4 ใช้ URL แชร์เดียวกัน ไม่ต้องกรอก GitHub Token

## ขั้นตอน A — สำรองข้อมูล GitHub ก่อน

1. เปิด Repository ที่เก็บข้อมูลปัจจุบันบน GitHub
2. เปิด `book_ids.json` แล้วกด Download / Raw และบันทึกสำรองไว้
3. อย่าอัปโหลดไฟล์ `book_ids.json` ตัวอย่างจาก ZIP นี้ไปทับไฟล์เดิม หากมีข้อมูลจริงอยู่แล้ว
4. หากเคยเลือก “จดจำ Token” ใน V3 ให้เปิดเว็บ V3 → ตั้งค่า → ออกจากระบบ เพื่อเอา Token ออกจากเบราว์เซอร์นั้น

## ขั้นตอน B — เตรียม GitHub Repository และ GitHub Pages

1. ใช้ Repository เดิมได้เลย (เช่น GitHub Username `myname`, Repo `novel-link-vault`)
2. ไปที่ Repository → **Add file → Upload files**
3. อัปโหลด/แทนที่ไฟล์เหล่านี้ใน root ของ Branch ที่ใช้เป็นหน้าเว็บ:

```
index.html
logo-2d.png
favicon-64.png
apple-touch-icon.png
icon-192.png
icon-512.png
manifest.webmanifest
```

4. กด Commit changes
5. ถ้ายังไม่ได้เปิด Pages: **Settings → Pages → Deploy from a branch → main → / (root) → Save**
6. ตรวจว่า URL หน้าเว็บ GitHub Pages เปิดได้ เช่น `https://myname.github.io/novel-link-vault/`

**ห้ามอัปโหลด:** GitHub Token, `VAULT_ACCESS_KEY`, `sync_config.local.json`, หรือไฟล์ `.env`

> หมายเหตุ: GitHub Pages เป็นเพียง **แหล่งเก็บหน้าเว็บและโลโก้** อย่าแชร์ GitHub Pages URL ให้เครื่องอื่นใช้เป็นแอป V4 เพราะ API ทำงานผ่าน **Worker URL** เท่านั้น

## ขั้นตอน C — ตรวจ GitHub Token (แก้ 404)

1. เปิด https://github.com/settings/personal-access-tokens
2. ใน Fine-grained Token ดู **Resource owner** ว่าเป็นเจ้าของ Repository จริง (ชื่อคน/องค์กร)
3. ใน **Repository access** เลือก **Only select repositories** และเลือก Repo ที่เก็บ `book_ids.json` จริง
4. ใน **Repository permissions** เลือก **Contents → Read and write** (หาโดยพิมพ์ `Contents` ไม่ใช่ `Read and write`)
5. ตรวจวันหมดอายุ Token ถ้าใกล้หมดอายุหรือเลือก Repo ผิด ให้แก้ไข/สร้างใหม่ตามสิทธิ์ที่ GitHub ให้ทำได้
6. จดค่าต่อไปนี้ไว้: **GH_OWNER**, **GH_REPO**, **GH_BRANCH**, **GITHUB_TOKEN** (ไม่ต้องส่งให้ใคร)

**สาเหตุ 404 ที่พบบ่อย:** `GH_OWNER` ไม่ตรงชื่อเจ้าของ Repo, ชื่อ Repo พิมพ์ผิด, Token ไม่ได้เลือก Repo นี้, Repo อยู่ในองค์กรแต่ตั้ง Resource owner ผิด, Branch ชื่อ `master` ไม่ใช่ `main`, ไฟล์ยังไม่ได้ Commit

## ขั้นตอน D — สร้าง Cloudflare Worker เพียงครั้งเดียว

1. สมัครหรือเข้าสู่ระบบ https://dash.cloudflare.com/
2. เลือก **Workers & Pages** → **Create application** → **Create Worker** (ชื่อเมนูอาจเปลี่ยนเล็กน้อย)
3. ตั้งชื่อ เช่น `novel-id-vault` → **Deploy**
4. เลือก Worker ที่สร้าง → **Edit code / Quick edit**
5. เปิดไฟล์ `cloudflare_worker.js` จากชุด ZIP แล้วคัดลอกโค้ดทั้งหมดไปแทนโค้ดตัวอย่างใน Cloudflare Editor → **Deploy**
6. ไปที่ Worker → **Settings → Variables and Secrets → Add** แล้วสร้างค่าตามตาราง

| ชื่อตัวแปร | ประเภท | ตัวอย่าง / ค่าที่ใส่ |
|---|---|---|
| `GH_OWNER` | Text | `myname` |
| `GH_REPO` | Text | `novel-link-vault` |
| `GH_BRANCH` | Text (ไม่บังคับ) | `main` หรือเว้นไว้เพื่อใช้ Default Branch |
| `SITE_URL` | Text | `https://myname.github.io/novel-link-vault/` |
| `GITHUB_TOKEN` | **Secret** | Fine-grained Token ของคุณ |
| `VAULT_ACCESS_KEY` | **Secret** | สุ่มรหัสลับยาวอย่างน้อย 24 ตัวอักษร |

7. กด Deploy/Save ให้ตัวแปรมีผล
8. Worker URL ของคุณจะมีรูปแบบ `https://novel-id-vault.ชื่อบัญชี.workers.dev/` ให้ใช้ URL นี้เป็นที่อยู่แอป V4

### วิธีสร้าง VAULT_ACCESS_KEY ที่ปลอดภัย

บน Windows ที่มี Python ให้เปิด Command Prompt ในโฟลเดอร์ ZIP แล้วรัน:

```bat
py -3 make_share_key.py
```

จะได้รหัสสุ่มยาวที่ไม่ต้องจำเอง คัดลอกใส่ Secret `VAULT_ACCESS_KEY` บน Cloudflare

> อย่านำรหัสนี้หรือ GitHub Token ไป Commit บน GitHub และอย่าเอาไปใส่ใน Worker source code แบบ hardcode ต้องตั้งเป็น **Secret** ใน Dashboard เท่านั้น

## ขั้นตอน E — เชื่อมเครื่องแรกและสร้างลิงก์แชร์

1. เปิด **Worker URL** ผ่าน Chrome บนคอม/มือถือ (ไม่ใช่ GitHub Pages URL)
2. หน้าจอแสดงโลโก้ 2D แล้วเปิดหน้าต่าง **เชื่อมต่อคลังออนไลน์**
3. วางค่า `VAULT_ACCESS_KEY` ที่ตั้งไว้บน Cloudflare (เป็นเพียงรหัสแชร์ **ไม่ใช่ GitHub Token**)
4. กด **เชื่อมต่อคลัง Book ID**
5. เมื่อสำเร็จ จะเห็นชื่อ `GH_OWNER/GH_REPO` และรายการ Book ID
6. กด **แชร์ลิงก์** บริเวณหัวเว็บเพื่อคัดลอกลิงก์ส่วนตัว

ตัวอย่าง URL (ไม่ใช่ของจริง):

```text
https://novel-id-vault.example.workers.dev/#access=รหัสแชร์แบบยาว
```

ลิงก์นี้มีรหัสสำหรับเข้าใช้คลังในส่วน `#access=` ไม่ใช่ GitHub Token ส่วนที่ขึ้นต้นด้วย `#` ไม่ถูกส่งเป็นพาธในคำขอ HTTP แต่ยังถือว่าเป็น **ความลับ** เพราะใครที่มีลิงก์ก็ใช้สิทธิ์นี้ได้

## ขั้นตอน F — ใช้บนมือถือหรือเครื่องอื่น (ไม่ต้องใส่ Token)

1. ส่ง **ลิงก์จากปุ่ม “แชร์ลิงก์”** ไปให้ตัวเองหรืออุปกรณ์ส่วนตัว (เช่น ผ่านแชตที่เชื่อถือได้)
2. เปิดใน Chrome หรือ Safari ของอุปกรณ์นั้น
3. เว็บจะอ่าน `#access=...` แล้วเชื่อมต่อ Worker อัตโนมัติ จากนั้นเก็บสถานะเข้าถึงไว้ในเบราว์เซอร์ของอุปกรณ์นั้น
4. วางลิงก์ Fanqie / Changdu แล้วกด **บันทึกลง GitHub** หรือกดเลข Book ID เพื่อคัดลอกและทำเครื่องหมายคัดลอกแล้ว
5. ถ้าอยากปักหน้าโฮมสกรีน Android: เปิด Worker URL ใน Chrome → เมนู `⋮` → **Add to Home screen / Install app** ตามตัวเลือกที่ปรากฏ
6. บน iPhone: เปิด Worker URL ด้วย Safari → Share → **Add to Home Screen** → Add

หลังติดตั้งไอคอน หากแอปโหมด Standalone ไม่ใช้ข้อมูลล็อกอินร่วมกับ Safari/Chrome หรือแสดงหน้าขอรหัสอีกครั้ง ให้เปิด **ลิงก์แชร์ฉบับเต็ม** ในแอปนั้นอีกครั้ง หรือกรอกรหัสแชร์หนึ่งครั้ง (ยังไม่ต้องใช้ GitHub Token)

## ขั้นตอน G — ซิงก์ Windows ลง D:\[ NOVEL ]\History

1. ลง Python 3.9 หรือใหม่กว่า
2. แตกไฟล์ ZIP V4 ในเครื่อง เช่น `D:\NovelVaultV4`
3. ดับเบิลคลิก `start_sync_windows.bat`
4. เมื่อถูกถาม ให้วาง **ลิงก์แชร์ส่วนตัวจากเว็บ** ที่มี `#access=` (ทำเพียงครั้งแรก)
5. โปรแกรมจะตรวจ Worker API และเก็บ URL ที่ใส่ไว้ใน `sync_config.local.json` **ในเครื่องเท่านั้น**
6. โปรแกรมซิงก์ทุก 45 วินาทีไปที่:

```
D:\[ NOVEL ]\History\book_ids.json
```

**คำเตือน:** `sync_config.local.json` มีรหัสเข้าถึงอยู่ ห้ามอัปโหลดหรือส่งต่อไฟล์นี้ ถ้าคอมใช้ร่วมกับคนอื่นควรป้องกันการอ่านไฟล์ดังกล่าว

หากต้องการซิงก์ครั้งเดียว:

```bat
py -3 sync_windows.py --once
```

## วิธีแก้ 404 ใหม่จาก API

ใน V4 เมื่อเชื่อมต่อ Worker แล้ว โปรแกรมจะตรวจเป็นลำดับดังนี้:

| รหัส | ความหมาย | แก้ไข |
|---|---|---|
| `REPO_NOT_FOUND` | ไม่พบ Repository หรือ Token ไม่ได้สิทธิ์ Repo นั้น | ตรวจ GH_OWNER, GH_REPO, Repository access ใน Token |
| `BRANCH_NOT_FOUND` | Branch ที่ระบุไม่มี | เปลี่ยน GH_BRANCH ให้ตรง (เช่น main/master) |
| `GITHUB_TOKEN_INVALID` | GitHub Token ไม่ถูกต้องหรือหมดอายุ | สร้าง/เปลี่ยน Token Secret |
| `GITHUB_WRITE_FORBIDDEN` | Token เขียนไม่ได้ | Contents: Read and write; ตรวจ Branch protection |
| `GITHUB_WRITE_NOT_FOUND` | เขียนหา Repo/Branch/ไฟล์ไม่เจอ | ตรวจค่า Repository, Branch, สิทธิ์ Token |
| `INVALID_ACCESS_KEY` | รหัสแชร์ไม่ตรง Cloudflare | เปิดลิงก์แชร์ล่าสุด หรือกรอก VAULT_ACCESS_KEY ให้ถูก |
| Static 502 | Worker เปิดหน้า GitHub Pages ไม่ได้ | ตรวจ SITE_URL และสถานะ Pages |

**ข้อมูลไม่หาย:** V4 ใช้รูปแบบเดิม `{"book_ids":[...], "copied_ids":[...]}` และไม่ลบรายการเก่า การเปลี่ยน Worker ไม่จำเป็นต้องสร้าง JSON ใหม่

## สิ่งที่ต้องระวัง

- เมื่อแชร์ลิงก์ คนที่ได้รับลิงก์จะสามารถเพิ่ม/คัดลอก/ทำเครื่องหมาย ID ได้ทั้งหมด ไม่มีบัญชีหรือสิทธิ์แยกรายบุคคล
- ถ้าต้องการหยุดให้ใครใช้ ให้เปลี่ยน **Secret `VAULT_ACCESS_KEY`** และแจก URL ใหม่ **ทุกอุปกรณ์ที่ยังใช้งานจะต้องรับลิงก์ใหม่**
- ถ้า GitHub Token หลุดหรือ Repo เข้าถึงไม่ได้ ต้องแก้ที่ GitHub และอัปเดต Secret `GITHUB_TOKEN`
- GitHub Pages `index.html` ต้องเป็น V4 ที่รองรับ Worker; อย่าใช้ V3 ร่วมกับ Worker URL
- GitHub Pages + Worker เป็นบริการภายนอก มีเงื่อนไข/โควตา และผู้ใช้ต้องจัดการบัญชีของตัวเอง
- เว็บไซต์รุ่นนี้เป็น **แชร์แบบผู้ถือกุญแจ (bearer-link)** ไม่ใช่ระบบบัญชีแยกผู้ใช้ หากต้องการแชร์ให้บุคคลอื่นที่ไม่เชื่อถือ ควรเพิ่มระบบล็อกอินและสิทธิ์แยกต่างหาก
