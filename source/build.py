# Builds two files from src.html + assets + fonts.css (run from this folder):
#  1) ../amber_msc_hub_combined.html  = everything in ONE file (works from a local file)
#  2) ../web/  = the PUBLISH folder: index.html (small, ~1 MB) + lib/*.js (loaded only when she imports a file) + sw.js, manifest, icons
import base64,os,shutil
h=os.path.dirname(os.path.abspath(__file__))
b=lambda p,m:'data:%s;base64,%s'%(m,base64.b64encode(open(os.path.join(h,p),'rb').read()).decode())
s=open(os.path.join(h,'src.html')).read()
s=s.replace('__LOGO__',b('assets/logo.png','image/png')).replace('__HERO__',b('assets/hero.jpg','image/jpeg')).replace('__FONTS__',open(os.path.join(h,'fonts.css')).read())
LIBS=[('MAMMOTH','mammoth.js'),('READXLSX','readxlsx.js'),('PDFJS','pdf.js'),('PDFWORKER','pdf.worker.js')]
full=s
for k,f in LIBS:
    full=full.replace('__LIB_%s__'%k,open(os.path.join(h,'assets','lib',f)).read().replace('</script','<\\/script'))
open(os.path.join(h,'..','amber_msc_hub_combined.html'),'w').write(full)
web=s
for k,f in LIBS: web=web.replace('__LIB_%s__'%k,'')
wd=os.path.join(h,'..','web');os.makedirs(os.path.join(wd,'lib'),exist_ok=True)
open(os.path.join(wd,'index.html'),'w').write(web)
for k,f in LIBS: shutil.copyfile(os.path.join(h,'assets','lib',f),os.path.join(wd,'lib',f))
for f in os.listdir(os.path.join(h,'pwa')):
    if not f.startswith('sw.BACKUP'): shutil.copyfile(os.path.join(h,'pwa',f),os.path.join(wd,f))
print('single file',len(full)//1024,'KB | web index.html',len(web)//1024,'KB')

# ---- tour check: warn when a tab or card has no tour step / ? hint ----
import re,html
raw=open(os.path.join(h,'src.html')).read()
def blk(a,z):
    i=raw.find(a);j=raw.find(z);return raw[i:j] if 0<=i<j else ''
tabs=re.findall(r"\['(\w+)','[^']*','[^']*'\]",re.search(r"const TABS=\[(.*?)\];",raw,re.S).group(1))
steps=re.findall(r"t:'(\w+)'",blk('/*TOUR*/','/*ENDTOUR*/'))
keys=re.findall(r"\['([^']+)',\"",blk('/*HINTS*/','/*ENDHINTS*/'))
ign=re.findall(r"'([^']+)'",blk('/*IGNORE*/','/*ENDIGNORE*/'))
bad=[t for t in tabs if t not in steps]
cards=[]
for m in re.findall(r'<h2[^>]*>(.*?)</h2>',raw,re.S):
    if '${' in m: continue
    t=re.sub(r'[^\x20-\x7e]','',html.unescape(re.sub('<[^>]+>','',m))).strip()
    if t and not any(k in t for k in keys) and not any(i in t for i in ign): cards.append(t)
if bad or cards:
    print('TOUR CHECK WARNING: add tour text for -> tabs:',bad,'cards:',cards)
else: print('TOUR CHECK ok')
