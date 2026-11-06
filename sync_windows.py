#!/usr/bin/env python3
"""Novel ID Vault — bidirectional additive sync between GitHub and Windows.

Requirements: Python 3.9+ with stdlib only. No third-party packages.
Secrets: GitHub token is read via NOVEL_GITHUB_TOKEN or entered at startup.
Never writes token into config, source code, or GitHub.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_FILE = r"D:\[ NOVEL ]\History\book_ids.json"
CONFIG_FILE = Path(__file__).resolve().parent / "sync_config.local.json"
NAME_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
BOOK_RE = re.compile(r"^\d{15,20}$")
API = "https://api.github.com"


class GitHubError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub HTTP {status}: {message}")
        self.status = status


def unique_ids(values):
    if not isinstance(values, list):
        raise ValueError('book_ids ต้องเป็นรายการ (Array)')
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not BOOK_RE.fullmatch(value):
            raise ValueError(f"ข้อมูลใน JSON ไม่ถูกต้อง: {str(value)[:35]}")
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def parse_json(text: str) -> dict:
    """Accept older book_ids-only files and current book_ids+copied_ids files."""
    obj = json.loads(text)
    if isinstance(obj, list):
        obj = {'book_ids': obj}
    if not isinstance(obj, dict) or 'book_ids' not in obj:
        raise ValueError('JSON ต้องมีรูปแบบ {"book_ids": ["..."], "copied_ids": ["..."]}')
    ids = unique_ids(obj['book_ids'])
    copied = unique_ids(obj.get('copied_ids', []))
    if not set(copied).issubset(ids):
        raise ValueError('copied_ids มี Book ID ที่ไม่มีใน book_ids')
    return {'book_ids': ids, 'copied_ids': copied}


def json_text(data: dict) -> str:
    ids = unique_ids(data['book_ids'])
    copied = set(unique_ids(data.get('copied_ids', [])))
    if not copied.issubset(ids):
        raise ValueError('copied_ids มี Book ID ที่ไม่มีใน book_ids')
    return json.dumps({'book_ids': ids, 'copied_ids': [id for id in ids if id in copied]},
                      indent=2, ensure_ascii=False) + '\n'


def read_local(path: Path) -> tuple[dict, bool]:
    if not path.is_file():
        return {'book_ids': [], 'copied_ids': []}, False
    return parse_json(path.read_text(encoding='utf-8-sig')), True


def write_local_atomic(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix='.novel_ids_',
                                         suffix='.tmp', delete=False) as handle:
            temp_name = handle.name
            handle.write(json_text(data))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)


def merge_books(remote: dict, local: dict) -> dict:
    """Preserve ID order and merge monotonic 'has ever copied' status."""
    ids = unique_ids(remote['book_ids'] + local['book_ids'])
    copied = set(remote['copied_ids']) | set(local['copied_ids'])
    return {'book_ids': ids, 'copied_ids': [id for id in ids if id in copied]}


class GitHubClient:
    def __init__(self, owner: str, repo: str, branch: str, token: str):
        if not NAME_RE.fullmatch(owner) or not REPO_RE.fullmatch(repo):
            raise ValueError('GitHub owner/repository ไม่ถูกต้อง')
        if not token:
            raise ValueError('กรุณาใส่ GitHub token')
        self.base = f'{API}/repos/{quote(owner)}/{quote(repo)}'
        self.branch = branch
        self.token = token
        self.repo_name = f'{owner}/{repo}'

    def request(self, method: str, endpoint: str, data: dict | None = None):
        payload = json.dumps(data).encode('utf-8') if data is not None else None
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + self.token,
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'Novel-ID-Vault-Sync/1.0',
        }
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(self.base + endpoint, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=25) as response:
                return response.status, json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            try:
                problem = json.loads(exc.read().decode('utf-8')).get('message', '')
            except (ValueError, UnicodeError):
                problem = exc.reason
            raise GitHubError(exc.code, str(problem)[:180]) from exc
        except URLError as exc:
            raise ConnectionError(f'เชื่อมต่อ GitHub ไม่ได้: {exc.reason}') from exc

    def check_repo(self):
        _, metadata = self.request('GET', '')
        if not self.branch:
            self.branch = metadata.get('default_branch') or ''
        if not self.branch:
            raise ValueError('Repository ยังไม่มี default branch; สร้าง commit แรกก่อน')
        self.request('GET', '/branches/' + quote(self.branch, safe=''))

    def get_ids(self) -> tuple[dict, str | None]:
        endpoint = f'/contents/book_ids.json?ref={quote(self.branch, safe="")}'
        try:
            _, data = self.request('GET', endpoint)
        except GitHubError as exc:
            if exc.status == 404:
                return {'book_ids': [], 'copied_ids': []}, None
            raise
        if data.get('type') != 'file' or data.get('encoding') != 'base64' or not data.get('content'):
            raise ValueError('GitHub API ไม่ส่งเนื้อหา book_ids.json (ไฟล์ใหญ่เกิน API หรือชนิดไม่ใช่ไฟล์)')
        content = base64.b64decode(data['content']).decode('utf-8-sig')
        return parse_json(content), data['sha']

    def put_ids(self, data: dict, sha: str | None):
        content = base64.b64encode(json_text(data).encode('utf-8')).decode('ascii')
        body = {'message': f'Sync novel IDs / copied state ({len(data["book_ids"])} total)',
                'content': content, 'branch': self.branch}
        if sha:
            body['sha'] = sha
        self.request('PUT', '/contents/book_ids.json', body)


def sync_once(client: GitHubClient, path: Path) -> tuple[int, int, int]:
    """Merge both sides safely. If upload fails, local file is not overwritten."""
    local, exists = read_local(path)
    for attempt in range(5):
        remote, sha = client.get_ids()
        merged = merge_books(remote, local)
        to_push = len(merged['book_ids']) - len(remote['book_ids'])
        try:
            # Upload also when the local JSON contains newly marked copied IDs.
            if merged != remote:
                client.put_ids(merged, sha)
            break
        except GitHubError as exc:
            if exc.status in (409, 422) and attempt < 4:
                print('  ตรวจพบการแก้ไขพร้อมกัน กำลังตรวจ GitHub อีกครั้ง...')
                continue
            raise
    else:
        raise RuntimeError('ไฟล์บน GitHub เปลี่ยนพร้อมกันหลายครั้ง ลองซิงก์ใหม่')
    if not exists or merged != local:
        write_local_atomic(path, merged)
    return len(merged['book_ids']), to_push, len(merged['book_ids']) - len(local['book_ids'])


def ask_config() -> dict:
    if CONFIG_FILE.is_file():
        config = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    else:
        print('ตั้งค่าการซิงก์ครั้งแรก (ชื่อ Owner/Repo เท่านั้น ไม่เก็บ Token)')
        owner = input('GitHub Username / Owner: ').strip()
        repo = input('Repository (เช่น novel-link-vault): ').strip()
        branch = input('Branch [main]: ').strip() or 'main'
        config = {'owner': owner, 'repo': repo, 'branch': branch,
                  'local_file': DEFAULT_FILE, 'interval_seconds': 45}
        if not NAME_RE.fullmatch(owner) or not REPO_RE.fullmatch(repo):
            raise ValueError('GitHub Owner หรือ Repo ไม่ถูกต้อง')
        CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'บันทึกการตั้งค่าที่ {CONFIG_FILE} (ไม่มี Token)')
    return config


def main():
    parser = argparse.ArgumentParser(description='Sync Novel Book IDs between local Windows and GitHub')
    parser.add_argument('--once', action='store_true', help='Sync exactly once and exit')
    parser.add_argument('--owner', help='GitHub owner (override config)')
    parser.add_argument('--repo', help='GitHub repository (override config)')
    parser.add_argument('--branch', help='Git branch (override config)')
    parser.add_argument('--file', dest='local_file', help='Local JSON file path (override config)')
    parser.add_argument('--interval', type=int, help='Seconds between syncs; default 45')
    args = parser.parse_args()

    config = ask_config() if not (args.owner and args.repo) else {}
    owner = args.owner or config.get('owner', '')
    repo = args.repo or config.get('repo', '')
    branch = args.branch if args.branch is not None else config.get('branch', 'main')
    target = Path(args.local_file or config.get('local_file', DEFAULT_FILE))
    interval = args.interval or int(config.get('interval_seconds', 45))
    if interval < 10:
        raise ValueError('ช่วงเวลาซิงก์ต้องไม่น้อยกว่า 10 วินาที')
    token = os.environ.get('NOVEL_GITHUB_TOKEN', '').strip()
    if not token:
        token = getpass.getpass('GitHub Fine-grained Token (จะไม่แสดงบนจอ): ').strip()
    client = GitHubClient(owner, repo, branch, token)
    print(f'กำลังตรวจ GitHub: {client.repo_name} ...')
    client.check_repo()
    print(f'เชื่อมต่อแล้ว: {client.repo_name} / {client.branch}')
    print(f'ไฟล์ Windows: {target}')
    print(f'โหมด: {"ซิงก์หนึ่งครั้ง" if args.once else f"ซิงก์ทุก {interval} วินาที (ปิดด้วย Ctrl+C)"}')
    print('-' * 60)
    while True:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            total, uploaded, downloaded = sync_once(client, target)
            print(f'[{now}] เรียบร้อย | ทั้งหมด {total} | เพิ่ม GitHub +{uploaded} | เพิ่ม Windows +{downloaded}', flush=True)
        except (ValueError, OSError, ConnectionError, GitHubError) as exc:
            print(f'[{now}] ซิงก์ไม่สำเร็จ: {exc}', file=sys.stderr, flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(interval)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, ConnectionError, GitHubError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print('\nหยุดซิงก์แล้ว')
            sys.exit(0)
        print(f'เกิดข้อผิดพลาด: {exc}', file=sys.stderr)
        sys.exit(1)
