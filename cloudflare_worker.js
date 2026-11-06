/*
 Novel ID Vault V4 — Cloudflare Worker GitHub bridge + static site gateway.
 One-time setup in Cloudflare Worker environment:
 GITHUB_TOKEN (Secret): Fine-grained token with Contents: Read/write for data repo
 VAULT_ACCESS_KEY (Secret): random string, min 24 characters. Share the *link* with #access=<key> only with trusted people.
 GH_OWNER (Text): GitHub username / org owning book_ids.json
 GH_REPO (Text): data repository name
 GH_BRANCH (Text, optional): branch, defaults to repository default branch
 SITE_URL (Text): public GitHub Pages URL including repo path and trailing /, e.g. https://username.github.io/novel-link-vault/
 Do not put secrets into index.html, this Worker source, GitHub files, or logs.
*/
const BASE_API = 'https://api.github.com';
const ID_RX = /^\d{15,20}$/;
const ALLOWED_STATIC = new Set([
  'index.html','logo-2d.png','favicon-64.png','apple-touch-icon.png',
  'icon-192.png','icon-512.png','manifest.webmanifest'
]);
const MAX_BODY_BYTES = 180000;
const JSON_HEADERS = {
  'content-type':'application/json; charset=utf-8',
  'cache-control':'no-store',
  'x-content-type-options':'nosniff',
  'referrer-policy':'no-referrer',
  'cross-origin-resource-policy':'same-origin'
};
function respond(obj,status=200) {
  return new Response(JSON.stringify(obj), {status, headers:JSON_HEADERS});
}
function fault(message, status=400, code='INVALID_REQUEST') {
  return respond({ok:false,code,message},status);
}
function ensureConfig(env) {
  for(const key of ['GITHUB_TOKEN','VAULT_ACCESS_KEY','GH_OWNER','GH_REPO','SITE_URL']) {
    if(!String(env[key]||'').trim()) throw new Error('ยังไม่ได้กำหนดค่า Worker: '+key);
  }
  if(String(env.VAULT_ACCESS_KEY).length < 24) throw new Error('VAULT_ACCESS_KEY ต้องยาวอย่างน้อย 24 ตัวอักษร');
  if(!/^[A-Za-z0-9-]{1,39}$/.test(env.GH_OWNER)) throw new Error('GH_OWNER ไม่ถูกต้อง');
  if(!/^[A-Za-z0-9._-]{1,100}$/.test(env.GH_REPO)) throw new Error('GH_REPO ไม่ถูกต้อง');
  const url=new URL(env.SITE_URL);
  if(url.protocol!=='https:' || (url.hostname!=='github.io' && !url.hostname.endsWith('.github.io'))) {
    throw new Error('SITE_URL ต้องเป็น GitHub Pages HTTPS (*.github.io)');
  }
}
function bytesEq(x,y) {
  const enc=new TextEncoder(); const a=enc.encode(x),b=enc.encode(y);
  if(a.length!==b.length) {crypto.subtle.timingSafeEqual(a,a);return false;}
  return crypto.subtle.timingSafeEqual(a,b);
}
function auth(req,env) {
  const raw=req.headers.get('authorization')||'';
  const m=/^Bearer ([^\s]+)$/.exec(raw);
  return !!m && bytesEq(m[1],String(env.VAULT_ACCESS_KEY));
}
function githubBase(env) {
  return `${BASE_API}/repos/${encodeURIComponent(env.GH_OWNER)}/${encodeURIComponent(env.GH_REPO)}`;
}
function apiHeaders(env,body=false) {
  const h={
    'Authorization':'Bearer '+env.GITHUB_TOKEN,
    'Accept':'application/vnd.github+json',
    'X-GitHub-Api-Version':'2022-11-28',
    'User-Agent':'Novel-ID-Vault-V4'
  };
  if(body) h['Content-Type']='application/json';
  return h;
}
async function github(env,path,method='GET',payload=null) {
  const init={method,headers:apiHeaders(env,!!payload),cache:'no-store'};
  if(payload) init.body=JSON.stringify(payload);
  const r=await fetch(githubBase(env)+path,init);
  let body=null;
  try {body=await r.json();} catch(e) {}
  return {status:r.status,body};
}
async function repositoryInfo(env) {
  const r=await github(env,'');
  if(r.status===404) throw Object.assign(new Error('ไม่พบ Repository หรือ Token ไม่ได้รับสิทธิ์สำหรับ Repository นี้ — ตรวจ GH_OWNER / GH_REPO / Repository access ใน Token'),{status:404,code:'REPO_NOT_FOUND'});
  if(r.status===401) throw Object.assign(new Error('GitHub Token ไม่ถูกต้องหรือหมดอายุ'),{status:502,code:'GITHUB_TOKEN_INVALID'});
  if(r.status===403) throw Object.assign(new Error('GitHub ปฏิเสธสิทธิ์เข้าถึง Repository (403)'),{status:502,code:'GITHUB_FORBIDDEN'});
  if(r.status!==200) throw Object.assign(new Error('ตรวจ Repository ไม่สำเร็จ (GitHub '+r.status+')'),{status:502,code:'GITHUB_ERROR'});
  const branch=String(env.GH_BRANCH||r.body?.default_branch||'').trim();
  if(!branch) throw Object.assign(new Error('ไม่พบ Default Branch ของ Repository'),{status:404,code:'NO_BRANCH'});
  const b=await github(env,'/branches/'+encodeURIComponent(branch));
  if(b.status!==200) throw Object.assign(new Error('ไม่พบ Branch '+branch+' หรือไม่มีสิทธิ์เข้าถึง ('+b.status+')'),{status:404,code:'BRANCH_NOT_FOUND'});
  return {branch,private:!!r.body?.private};
}
function uniqueIds(values) {
  if(!Array.isArray(values)) throw Object.assign(new Error('book_ids และ copied_ids ต้องเป็น Array'),{status:422});
  const out=[],seen=new Set();
  for(const id of values) {
    if(typeof id!=='string' || !ID_RX.test(id)) throw Object.assign(new Error('Book ID ไม่ถูกต้อง: '+String(id).slice(0,30)),{status:422});
    if(!seen.has(id)) {seen.add(id);out.push(id);}
  }
  return out;
}
function parseFile(content) {
  let raw=JSON.parse(content);
  if(Array.isArray(raw)) raw={book_ids:raw};
  if(!raw||typeof raw!=='object') throw new Error('book_ids.json ไม่ใช่ Object');
  const ids=uniqueIds(raw.book_ids),copied=uniqueIds(raw.copied_ids||[]);
  const seen=new Set(ids);
  if(copied.some(x=>!seen.has(x))) throw new Error('copied_ids มีเลขที่ไม่อยู่ใน book_ids');
  return {book_ids:ids,copied_ids:copied};
}
function decodeB64(base64) {
  const binary=atob(base64.replace(/\s/g,''));
  return new TextDecoder().decode(Uint8Array.from(binary,c=>c.charCodeAt(0)));
}
function encodeB64(str) {
  const bytes=new TextEncoder().encode(str);
  let binary='';
  for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
  return btoa(binary);
}
async function readBooks(env,branch) {
  const r=await github(env,'/contents/book_ids.json?ref='+encodeURIComponent(branch));
  if(r.status===404) return {data:{book_ids:[],copied_ids:[]},sha:null,exists:false};
  if(r.status!==200) throw Object.assign(new Error('อ่าน book_ids.json ไม่สำเร็จ (GitHub '+r.status+'): '+String(r.body?.message||'').slice(0,100)),{status:502,code:'GITHUB_READ_FAILED'});
  if(!r.body || r.body.encoding!=='base64'||typeof r.body.content!=='string') throw Object.assign(new Error('ไฟล์ book_ids.json ใหญ่เกินหรือ GitHub ส่งรูปแบบที่ไม่รองรับ'),{status:502,code:'INVALID_FILE'});
  return {data:parseFile(decodeB64(r.body.content)),sha:r.body.sha,exists:true};
}
function mergeBooks(remote, add, marks) {
  const ids=uniqueIds(remote.book_ids.concat(add));
  const known=new Set(ids);
  const copied=new Set(remote.copied_ids);
  for(const id of marks) if(known.has(id))copied.add(id);
  return {book_ids:ids,copied_ids:ids.filter(x=>copied.has(x))};
}
async function writeBooks(env,branch,sha,data) {
  const payload={
    message:`Novel ID Vault update (${data.book_ids.length} IDs)`,
    content:encodeB64(JSON.stringify(data,null,2)+'\n'),
    branch
  };
  if(sha)payload.sha=sha;
  return github(env,'/contents/book_ids.json','PUT',payload);
}
async function apiRequest(request,env,route) {
  if(!auth(request,env))return fault('ลิงก์เข้าใช้งานไม่ถูกต้อง หรือรหัสแชร์ถูกเปลี่ยน',401,'INVALID_ACCESS_KEY');
  const info=await repositoryInfo(env);
  if(route==='/api/health') {
    const book=await readBooks(env,info.branch);
    return respond({ok:true,owner:env.GH_OWNER,repo:env.GH_REPO,branch:info.branch,bookFileExists:book.exists,total:book.data.book_ids.length});
  }
  if(route==='/api/books' && request.method==='GET') {
    const book=await readBooks(env,info.branch);
    return respond({ok:true,...book.data});
  }
  if(route==='/api/books' && request.method==='POST') {
    const origin=request.headers.get('origin');
    if(origin && origin!==new URL(request.url).origin)return fault('ต้องเปิดเว็บผ่าน Worker URL เดียวกัน',403,'BAD_ORIGIN');
    const len=Number(request.headers.get('content-length')||0);
    if(len>MAX_BODY_BYTES)return fault('ข้อมูลที่ส่งมาใหญ่เกินไป',413,'TOO_LARGE');
    let raw='';
    try {raw=await request.text();} catch(e) {return fault('อ่านข้อมูลที่ส่งมาไม่สำเร็จ');}
    if(new TextEncoder().encode(raw).length>MAX_BODY_BYTES)return fault('ข้อมูลที่ส่งมาใหญ่เกินไป',413,'TOO_LARGE');
    let body;
    try{body=JSON.parse(raw);}catch(e){return fault('รูปแบบ JSON ที่ส่งมาไม่ถูกต้อง');}
    if(!body||typeof body!=='object'||!Array.isArray(body.add_ids)||!Array.isArray(body.mark_copied))return fault('ต้องส่ง add_ids และ mark_copied เป็น Array');
    const add=uniqueIds(body.add_ids),marks=uniqueIds(body.mark_copied);
    if(add.length>1000||marks.length>2000)return fault('จำกัดเพิ่ม 1000 และทำเครื่องหมาย 2000 Book ID ต่อครั้ง',413,'TOO_MANY');
    for(let attempt=0;attempt<6;attempt++) {
      const old=await readBooks(env,info.branch);
      const merged=mergeBooks(old.data,add,marks);
      const changed=merged.book_ids.length!==old.data.book_ids.length || merged.copied_ids.length!==old.data.copied_ids.length;
      if(!changed)return respond({ok:true,added:0,marked:0,unchanged:true,...old.data});
      const r=await writeBooks(env,info.branch,old.sha,merged);
      if(r.status===200||r.status===201) {
        return respond({ok:true,added:merged.book_ids.length-old.data.book_ids.length,marked:merged.copied_ids.length-old.data.copied_ids.length,...merged});
      }
      if(r.status===409||r.status===422) {
        if(attempt<5)continue;
        return fault('มีการอัปเดตพร้อมกันหลายครั้ง กรุณากดลองใหม่',409,'CONFLICT');
      }
      if(r.status===404)return fault('GitHub ไม่พบไฟล์/Branch/Repository ตอนเขียน — ตรวจสิทธิ์ Contents: Read and write ใน Token',502,'GITHUB_WRITE_NOT_FOUND');
      if(r.status===403)return fault('Token ไม่มีสิทธิ์ Contents: Read and write หรือ Branch ถูกป้องกัน',502,'GITHUB_WRITE_FORBIDDEN');
      return fault('GitHub เขียนไฟล์ไม่สำเร็จ ('+r.status+'): '+String(r.body?.message||'').slice(0,140),502,'GITHUB_WRITE_FAILED');
    }
  }
  return fault('ไม่พบ API นี้',404,'UNKNOWN_API');
}
async function staticFile(request,env,path) {
  const name=path==='/'?'index.html':path.slice(1);
  if(!ALLOWED_STATIC.has(name))return new Response('Not found',{status:404});
  const base=env.SITE_URL.endsWith('/')?env.SITE_URL:env.SITE_URL+'/';
  const uri=new URL(name,base);
  const r=await fetch(uri.toString(),{method:'GET',headers:{Accept:'*/*'},redirect:'follow',cf:{cacheTtl:0}});
  if(!r.ok) {
    if(name==='index.html')return new Response('ไม่พบหน้าเว็บบน GitHub Pages ('+r.status+') — ตรวจ SITE_URL และ Pages deployment',{status:502,headers:{'content-type':'text/plain; charset=utf-8'}});
    return new Response('Static asset not found ('+r.status+')',{status:404});
  }
  const h=new Headers();
  h.set('content-type', r.headers.get('content-type')||'application/octet-stream');
  h.set('cache-control',name==='index.html'?'no-store':'public,max-age=3600');
  h.set('referrer-policy','no-referrer');
  h.set('x-content-type-options','nosniff');
  return new Response(r.body,{status:200,headers:h});
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    try{
      ensureConfig(env);
      if(url.pathname.startsWith('/api/')){
        if(!['GET','POST'].includes(request.method))return fault('ไม่รองรับ HTTP method นี้',405,'METHOD_NOT_ALLOWED');
        return await apiRequest(request,env,url.pathname);
      }
      if(request.method!=='GET'&&request.method!=='HEAD')return new Response('Method not allowed',{status:405});
      return await staticFile(request,env,url.pathname);
    }catch(e){
      if(url.pathname.startsWith('/api/'))return fault(String(e.message||'Server Error'),e.status||500,e.code||'SERVER_ERROR');
      return new Response('Cloudflare Worker: '+String(e.message||'Server Error'),{status:500,headers:{'content-type':'text/plain; charset=utf-8'}});
    }
  }
};
