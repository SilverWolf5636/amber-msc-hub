import os,re
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'src.html')
s=open(p,encoding='utf-8').read()
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(s.count(a),a[:90])
    s=s.replace(a,b)

# ---- defaults: backup bookkeeping
rep("stickies:[],alarms:[]};\n}","stickies:[],alarms:[],lastBackup:0,born:Date.now(),bkSnooze:0};\n}")

# ---- load / save with checks, safe copy, warnings
old_load="function load(){const d=defaults();try{const r=localStorage.getItem(KEY);if(r){const p=JSON.parse(r);const o=Object.assign(d,p);o.invOn=true;if(!Array.isArray(o.catalog))o.catalog=[];return o}}catch(e){}return d}\nfunction save(){try{localStorage.setItem(KEY,JSON.stringify(S));return true}catch(e){return false}}"
new_load=r"""const OBJARR=['notes','live_tasks','shows','tasks','restock','orders','docs','contacts','groups','closeList','sops','stickies','alarms','playlists','tracks','media','walls','customLooks','team'];
let LOADWARN='',RAWBAD='',BKPEND=null,SAVEFAIL=false,lastPrev=0;
const isObj=x=>x&&typeof x==='object'&&!Array.isArray(x);
const objs=a=>Array.isArray(a)?a.filter(x=>x&&typeof x==='object'):[];
/* make any stored/restored data safe to use: right types, no null items, no missing lists */
function fixShape(o){const d=defaults();
 Object.keys(d).forEach(k=>{const dv=d[k],v=o[k];
  if(Array.isArray(dv)){if(!Array.isArray(v))o[k]=dv;else if(OBJARR.includes(k))o[k]=objs(v)}
  else if(isObj(dv)){if(!isObj(v))o[k]=dv;else Object.keys(dv).forEach(s=>{const a=dv[s],b=v[s];if(Array.isArray(a)){if(!Array.isArray(b))v[s]=a}else if(isObj(a)){if(!isObj(b))v[s]=a}else if(a!==null&&typeof a!==typeof b)v[s]=a})}
  else if(dv!==null&&typeof dv!==typeof v)o[k]=dv});
 if(!isObj(o.walk))o.walk=d.walk;Object.keys(o.walk).forEach(k=>{o.walk[k]=objs(o.walk[k])});
 if(!isObj(o.staff))o.staff=d.staff;Object.keys(d.staff).forEach(k=>{if(!Array.isArray(o.staff[k]))o.staff[k]=[]});Object.keys(o.staff).forEach(k=>{o.staff[k]=objs(o.staff[k])});
 o.sops.forEach(x=>{if(!Array.isArray(x.steps))x.steps=[];if(!Array.isArray(x.done))x.done=[]});
 o.mod.walk=objs(o.mod.walk);o.mod.log=objs(o.mod.log);o.ev.miles=objs(o.ev.miles);o.ev.tasks=objs(o.ev.tasks);
 ['wd','we'].forEach(k=>{const h=o.hrs[k];if(!Array.isArray(h)||h.length<2||!isFinite(h[0])||!isFinite(h[1]))o.hrs[k]=d.hrs[k]});
 o.invOn=true;if(!Array.isArray(o.catalog))o.catalog=[];return o}
function load(){const d=defaults();let raw=null;try{raw=localStorage.getItem(KEY)}catch(e){}
 if(raw){try{const p=JSON.parse(raw);if(!isObj(p))throw 0;return fixShape(Object.assign(d,p))}
  catch(e){RAWBAD=raw;LOADWARN='corrupt';try{if(!localStorage.getItem(KEY+'_corrupt'))localStorage.setItem(KEY+'_corrupt',raw)}catch(_){}}}
 return d}
function wbar(id,html){let b=$(id);if(!b){b=document.createElement('div');b.id=id;b.className='wbar';b.setAttribute('role','alert');document.body.appendChild(b)}b.innerHTML=html}
function saveWarn(on){const b=$('saveWarn');if(!on){if(b)b.remove();return}
 wbar('saveWarn','<b>&#9888; Not saved.</b> This phone is out of space, so your newest changes are not being kept. <button class="btn sm" data-a="saveWarnCopy">Copy my data now</button>')}
function loadWarnShow(){if(LOADWARN==='corrupt')wbar('loadWarn','<b>&#9888; Your saved data could not be read,</b> so the app started fresh. A copy of the old data was kept on this phone. <button class="btn sm" data-a="copyBad">Copy the old data</button> <button class="btn sm alt" data-a="loadWarnOk">OK</button>')}
/* save: keeps a safe copy of the previous state (at most every 10 minutes) and warns if the phone is full */
function save(){let s;try{s=JSON.stringify(S)}catch(e){return false}
 try{let old=null;try{old=localStorage.getItem(KEY)}catch(_){}
  try{localStorage.setItem(KEY,s)}catch(e){localStorage.removeItem(KEY+'_prev');localStorage.removeItem(KEY+'_corrupt');localStorage.setItem(KEY,s)}
  if(old&&old!==s&&Date.now()-lastPrev>6e5){lastPrev=Date.now();try{localStorage.setItem(KEY+'_prev',old)}catch(_){}}
  if(SAVEFAIL){SAVEFAIL=false;saveWarn(false)}
  return true}
 catch(e){if(!SAVEFAIL){SAVEFAIL=true;saveWarn(true)}return false}}"""
rep(old_load,new_load)

# ---- backup helpers (placed after toast/copyText definitions)
anchor="/* ---------- time ---------- */"
helpers=r"""/* ---------- backup file, restore, reminder ---------- */
const blobToURL=b=>new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(b)});
async function dlBackup(){
 const out={app:'msc-hub-backup',v:2,saved:new Date().toISOString(),state:S,photos:{}};let left=0,total=0;
 for(const m of (S.media||[])){try{const b=await idbGet(m.id);if(!b)continue;if((b.type||'').indexOf('video')===0||b.size>25e6||total+b.size>120e6){left++;continue}total+=b.size;out.photos[m.id]=await blobToURL(b)}catch(e){left++}}
 const blob=new Blob([JSON.stringify(out)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='amber-hub-backup-'+todayISO()+'.json';document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},4000);
 S.lastBackup=Date.now();save();bkBannerRender();toast(left?'Backup file saved. '+left+' big video(s) or picture(s) were left out.':'Backup file saved')}
function applyRestore(p,photos){
 const beforeS=S;try{localStorage.setItem(KEY+'_prev',JSON.stringify(S))}catch(_){}
 try{const keep={media:S.media,show:S.show,lookShow:S.lookShow};const n=Object.assign(defaults(),p);if(!Array.isArray(p.media))n.media=keep.media;if(!p.show)n.show=keep.show;if(!p.lookShow)n.lookShow=keep.lookShow;S=fixShape(n);renderAll();migrateWalls();lastPrev=0;save();
  if(photos)Object.keys(photos).forEach(id=>{fetch(photos[id]).then(r=>r.blob()).then(b=>{delete MEDP[id];return idbPut(id,b)}).then(()=>{try{renderLook()}catch(_){}}).catch(()=>{})});
  return true}catch(err){S=beforeS;try{renderAll()}catch(_){}save();return false}}
function bkInfo(){const e=$('bkInfo');if(!e)return;const t=S.lastBackup;e.textContent=t?'Last backup: '+new Date(t).toLocaleDateString([],{month:'short',day:'numeric'})+' ('+Math.floor((Date.now()-t)/864e5)+' days ago).':'You have not made a backup yet.'}
function bkBannerRender(){const b=$('bkBanner');if(!b)return;const ref=Math.max(S.lastBackup||0,S.born||Date.now()),days=Math.floor((Date.now()-ref)/864e5),show=days>=7&&!((S.bkSnooze||0)>Date.now());b.style.display=show?'':'none';
 if(show)b.innerHTML='<div class="hd"><h2 style="font-size:.95rem">&#128190; Time for a backup</h2></div><div class="sub">'+(S.lastBackup?'Your last backup was '+days+' days ago.':'You have not made a backup yet.')+' A backup file keeps your data and pictures safe if this phone is lost or reset.</div><div class="row"><button class="btn sm" data-a="bkNow">Save a backup file</button><button class="btn sm alt" data-a="bkLater">Not now</button></div>';bkInfo()}
function validBackup(x){return isObj(x)&&Object.keys(defaults()).some(k=>k in x)}
function bkFileInit(){const f=$('bkFile');if(!f)return;f.addEventListener('change',async()=>{const file=f.files[0];f.value='';if(!file)return;const st=$('bkStatus');
 try{if(file.size>150e6)throw 0;const j=JSON.parse(await file.text()),state=j&&j.app==='msc-hub-backup'?j.state:j;if(!validBackup(state))throw 0;BKPEND={state,photos:(j&&j.photos)||null};const n=Object.keys(BKPEND.photos||{}).length;
  st.innerHTML='File ready ('+esc(file.name)+(n?', with '+n+' picture'+(n>1?'s':''):'')+'). <button class="btn sm red" data-a="bkApply">Replace everything with this file</button>'}
 catch(e){BKPEND=null;st.textContent='That file did not work.'}})}

"""
rep(anchor,helpers+anchor)

# ---- actions
i=s.index(" case'restore':try{")
j=s.index("\n",i)
newcases=r""" case'restore':{let p;try{p=JSON.parse($('backupBox').value.trim())}catch(e){toast('That backup text did not work');return}
  if(!validBackup(p)){toast('That backup text did not work');return}
  if(!el.dataset.arm){el.dataset.arm='1';el.textContent='Tap again to replace everything';setTimeout(()=>{if(el.isConnected){el.dataset.arm='';el.textContent='Restore from text below'}},6000);return}
  el.dataset.arm='';el.textContent='Restore from text below';toast(applyRestore(p,null)?'Restored. "Go back to the safe copy" undoes it.':'That backup did not fit the app. Nothing was changed.');return}
 case'restorePrev':{let r=null;try{r=localStorage.getItem(KEY+'_prev')}catch(e){}if(!r){toast('No safe copy yet');return}
  if(!el.dataset.arm){el.dataset.arm='1';el.textContent='Tap again to go back';setTimeout(()=>{if(el.isConnected){el.dataset.arm='';el.textContent='Go back to the safe copy'}},6000);return}
  el.dataset.arm='';el.textContent='Go back to the safe copy';try{const p=JSON.parse(r);if(!validBackup(p))throw 0;toast(applyRestore(p,null)?'Went back to the safe copy':'The safe copy did not fit the app')}catch(e){toast('The safe copy could not be read')}return}
 case'dlBackup':case'bkNow':dlBackup();return;
 case'loadBackupFile':$('bkFile').click();return;
 case'bkApply':{if(!BKPEND)return;if(!el.dataset.arm){el.dataset.arm='1';el.textContent='Tap again to replace everything';setTimeout(()=>{if(el.isConnected){el.dataset.arm='';el.textContent='Replace everything with this file'}},6000);return}
  const ok=applyRestore(BKPEND.state,BKPEND.photos);BKPEND=null;$('bkStatus').textContent='';toast(ok?'Restored from file':'That file did not fit the app. Nothing was changed.');return}
 case'bkLater':S.bkSnooze=Date.now()+3*864e5;save();bkBannerRender();return;
 case'saveWarnCopy':copyText(JSON.stringify(S),'Backup copied');return;
 case'copyBad':copyText(RAWBAD,'Copied');return;
 case'loadWarnOk':{const b=$('loadWarn');if(b)b.remove();return}"""
s=s[:i]+newcases+s[j:]
rep("case'copyBackup':copyText(JSON.stringify(S),'Backup copied');break;","case'copyBackup':copyText(JSON.stringify(S),'Backup copied');S.lastBackup=Date.now();bkBannerRender();break;")

# ---- html
rep("""  <div class="sub">Everything is saved on this device only. Copy a backup now and then and keep it somewhere safe.</div>
  <div class="row"><button class="btn sm" data-a="backup">Show backup text</button>""","""  <div class="sub">Everything is saved on this device only. Make a backup file now and then and keep it somewhere safe.</div>
  <div class="small" id="bkInfo"></div>
  <div class="row" style="margin:.4rem 0"><button class="btn sm gold" data-a="dlBackup">Save a backup file</button><button class="btn sm alt" data-a="loadBackupFile">Open a backup file</button><button class="btn sm alt" data-a="restorePrev">Go back to the safe copy</button></div>
  <input type="file" id="bkFile" accept=".json,application/json,text/plain" hidden>
  <div class="small" id="bkStatus" role="status"></div>
  <div class="row"><button class="btn sm" data-a="backup">Show backup text</button>""")
rep(' <div class="card c4" id="tourBanner" style="display:none"></div>',' <div class="card c4" id="bkBanner" style="display:none"></div>\n <div class="card c4" id="tourBanner" style="display:none"></div>')

# ---- css
rep(".hclock.ringing,.pcb.ringing{",""".wbar{position:fixed;left:.6rem;right:.6rem;bottom:.6rem;z-index:2500;background:#7f1d1d;color:#fff;border:2px solid #fff;border-radius:14px;padding:.7rem .9rem;font-size:.85rem;box-shadow:0 8px 24px rgba(0,0,0,.45)}
.wbar+.wbar{bottom:6.2rem}
.wbar .btn{margin:.3rem .3rem 0 0;background:#fff;color:#7f1d1d}
.hclock.ringing,.pcb.ringing{""")

# ---- boot
rep("setInterval(lookTick,10000);checkTeamLink();","setInterval(lookTick,10000);checkTeamLink();loadWarnShow();bkBannerRender();bkFileInit();")
open(p,'w',encoding='utf-8').write(s);print('stage1 patched')
