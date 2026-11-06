#!/usr/bin/env python3
"""Novel ID Vault V4: bidirectional, append-only sync through Cloudflare Worker.

Paste the private Share Link once on your own PC. Never need GitHub PAT here.
The local configuration stores the share key — keep the config file private.
Python 3.9+ standard library only.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_FILE = r'D:\[ NOVEL ]\History\book_ids.json'
CONFIG = Path(__file__).resolve().parent / 'sync_config.local.json'
BOOK = re.compile(r'^\d{15,20}$')


def unique(values):
    if not isinstance(values, list):
        raise ValueError('book_ids และ copied_ids ต้องเป็น Array')
    result = []
    seen = set()
    for item in values:
        if not isinstance(item, str) or not BOOK.fullmatch(item):
            raise ValueError('Book ID ในไฟล์ไม่ถูกต้อง: '+str(item)[:30])
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def parse_books(raw):
    if isinstance(raw, list):
        raw = {'book_ids': raw}
    if not isinstance(raw, dict):
        raise ValueError('ไฟล์ book_ids.json ต้องเป็น Object')
    ids = unique(raw.get('book_ids'))
    copied = unique(raw.get('copied_ids', []))
    if not set(copied).issubset(ids):
        raise ValueError('copied_ids มี ID ที่ไม่อยู่ใน book_ids')
    return {'book_ids': ids, 'copied_ids': copied}


def read_file(path):
    if not path.exists():
        return {'book_ids': [], 'copied_ids': []}, False
    return parse_books(json.loads(path.read_text(encoding='utf-8-sig'))), True


def write_file(path, books):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n', dir=path.parent,
                                         prefix='.novel_vault_', suffix='.tmp', delete=False) as f:
            tmp = f.name
            json.dump(books, f, indent=2, ensure_ascii=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def parse_share_link(link):
    link = link.strip()
    u = urlsplit(link)
    if u.scheme != 'https' or not u.netloc or u.username or u.password:
        raise ValueError('ลิงก์ต้องเป็น HTTPS ของ Cloudflare Worker หรือโดเมนที่ตั้งค่าเอง')
    key = parse_qs(u.fragment, keep_blank_values=False).get('access', [''])[0].strip()
    if len(key) < 24:
        raise ValueError('ลิงก์ไม่พบรหัสแชร์ที่ถูกต้อง — ต้องมี #access=...')
    origin = f'{u.scheme}://{u.netloc}'
    return origin, key


class WorkerClient:
    def __init__(self, origin, key):
        self.origin = origin.rstrip('/')
        self.key = key

    def request(self, method, route, payload=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        headers = {'Authorization':'Bearer '+self.key, 'Accept':'application/json',
                   'User-Agent':'Novel-ID-Vault-Windows/4.0'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(self.origin+route, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=35) as r:
                doc = json.loads(r.read().decode('utf-8'))
        except HTTPError as e:
            try:
                err = json.loads(e.read().decode('utf-8'))
                msg = err.get('message') or str(e)
            except (ValueError, UnicodeError):
                msg = str(e)
            raise RuntimeError(f'Worker ตอบ HTTP {e.code}: {msg}') from e
        except URLError as e:
            raise ConnectionError(f'เชื่อม Cloudflare Worker ไม่ได้: {e.reason}') from e
        if not isinstance(doc, dict) or doc.get('ok') is not True:
            raise RuntimeError(doc.get('message', 'รูปแบบ API ตอบกลับไม่ถูกต้อง') if isinstance(doc, dict) else 'API ตอบกลับผิดรูปแบบ')
        return doc

    def health(self):
        return self.request('GET', '/api/health')

    def get_books(self):
        return parse_books(self.request('GET', '/api/books'))

    def merge_books(self, add, marks):
        result = None
        add = unique(add); marks = unique(marks)
        size = max(len(add), len(marks))
        for i in range(0, max(size, 1), 1000):
            result = self.request('POST', '/api/books', {
                'add_ids':add[i:i+1000], 'mark_copied':marks[i:i+1000]
            })
        return parse_books(result)


def sync_once(client, local_path):
    local, exists = read_file(local_path)
    remote = client.get_books()
    remote_ids = set(remote['book_ids']); remote_copied = set(remote['copied_ids'])
    add = [x for x in local['book_ids'] if x not in remote_ids]
    marks = [x for x in local['copied_ids'] if x not in remote_copied]
    latest = client.merge_books(add, marks) if add or marks else remote
    # Keep all locally existing IDs/statuses (append-only)
    combined = unique(latest['book_ids'] + local['book_ids'])
    marked = set(latest['copied_ids']) | set(local['copied_ids'])
    merged = {'book_ids':combined, 'copied_ids':[x for x in combined if x in marked]}
    if not exists or merged != local:
        write_file(local_path, merged)
    return len(combined), len(add), len(combined)-len(local['book_ids'])


def main():
    ap = argparse.ArgumentParser(description='Novel ID Vault Worker -> Windows JSON sync')
    ap.add_argument('--once', action='store_true', help='ซิงก์ครั้งเดียว')
    ap.add_argument('--url', help='ลิงก์ส่วนตัวจากปุ่มแชร์ลิงก์ในเว็บ')
    ap.add_argument('--file', dest='local_file', help='พาธไฟล์ JSON ใน Windows')
    ap.add_argument('--interval', type=int, help='รอบซิงก์ (วินาที)')
    args = ap.parse_args()
    saved = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    share_link = args.url or saved.get('share_link', '')
    if not share_link:
        print('ตั้งค่าครั้งแรก: วางลิงก์ส่วนตัวจากปุ่ม “แชร์ลิงก์” ของเว็บ (ไม่ใช่ GitHub Token)')
        share_link = input('ลิงก์แชร์ส่วนตัว: ').strip()
    origin, key = parse_share_link(share_link)
    local_path = Path(args.local_file or saved.get('local_file', DEFAULT_FILE))
    interval = int(args.interval or saved.get('interval_seconds', 45))
    if interval < 10:
        raise ValueError('ช่วงเวลาซิงก์ต้องไม่น้อยกว่า 10 วินาที')
    client = WorkerClient(origin, key)
    info = client.health()
    print('เชื่อมต่อสำเร็จ:', info['owner']+'/'+info['repo'], 'Branch:', info['branch'])
    if not args.url and saved.get('share_link') != share_link:
        print('หมายเหตุ: ไฟล์ sync_config.local.json มีรหัสเข้าถึงอยู่ ห้ามแชร์หรืออัปโหลดขึ้น GitHub')
        CONFIG.write_text(json.dumps({'share_link':share_link, 'local_file':str(local_path),
                                      'interval_seconds':interval}, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('ไฟล์ Windows:', local_path)
    print('โหมด:', 'ซิงก์ครั้งเดียว' if args.once else f'ทุก {interval} วินาที (Ctrl+C เพื่อหยุด)')
    print('-'*60)
    while True:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            total, uploaded, downloaded = sync_once(client, local_path)
            print(f'[{now}] สำเร็จ | ทั้งหมด {total} | เพิ่มบน GitHub +{uploaded} | เพิ่มในเครื่อง +{downloaded}', flush=True)
        except (RuntimeError, ValueError, OSError, ConnectionError) as e:
            print(f'[{now}] ซิงก์ไม่สำเร็จ: {e}', file=sys.stderr, flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(interval)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nหยุดซิงก์แล้ว')
    except (RuntimeError, ValueError, OSError, ConnectionError) as exc:
        print('ข้อผิดพลาด:', exc, file=sys.stderr)
        sys.exit(1)
