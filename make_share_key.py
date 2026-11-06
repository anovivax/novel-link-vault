"""Generate a new secure random VAULT_ACCESS_KEY locally. Run: py -3 make_share_key.py"""
import secrets
print('\nVAULT_ACCESS_KEY = '+secrets.token_urlsafe(36)+'\n')
print('คัดลอกค่าไปใส่ Cloudflare Worker Secret ชื่อ VAULT_ACCESS_KEY อย่าโพสต์ลง GitHub')
