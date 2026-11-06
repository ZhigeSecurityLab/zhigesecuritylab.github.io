'use strict';
let state, profile, lang='en', dirty=false, busy=false, timer, connectionWaiting=false;
const $=id=>document.getElementById(id);
const defaults=['assets/people/default-male.svg','assets/people/default-female.svg'];
const templates={
  en:'## Biography\n\nWrite a short introduction.\n\n## Research Interests\n\n- Research topic 1\n- Research topic 2\n\n## Selected Publications\n\n- Add representative publications with links.\n\n## Projects and Service\n\nDescribe projects or academic service if relevant.\n',
  zh:'## 个人简介\n\n在这里填写简短介绍。\n\n## 研究方向\n\n- 研究方向一\n- 研究方向二\n\n## 代表性论文\n\n- 添加论文及链接。\n\n## 项目与学术服务\n\n根据需要填写。\n'
};
function message(value,good=false){$('message').textContent=value;$('message').className=good?'success':'';}
function changed(){dirty=true;message('有尚未保存的修改。');}
async function api(path,payload){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Editor-Token':state.token},body:JSON.stringify(payload)});const result=await response.json();if(!response.ok)throw Error(result.error||'操作失败');return result;}
function category(){return $('category').value;}
function remoteUrl(language){return state.branch==='main'?'https://zhigesecuritylab.github.io/'+path(language):'https://github.com/ZhigeSecurityLab/zhigesecuritylab.github.io/tree/'+state.branch;}
function path(language){return (language==='zh'?'zh/':'')+'people/'+category()+'/';}
function capture(){if(!profile)return;profile[lang].bio_markdown=$('markdown').value;profile[lang].description=$('description').value;profile.category=category();}
function render(){
  if(!profile)return;
  for(const language of ['en','zh'])for(const key of ['name','role','url'])$(`${language}-${key}`).value=profile[language][key]||'';
  $('category').value=profile.category;
  $('markdown').value=profile[lang].bio_markdown||'';$('description').value=profile[lang].description||'';
  document.querySelectorAll('[data-lang]').forEach(button=>button.classList.toggle('active',button.dataset.lang===lang));
  const rich=['faculty','postdocs'].includes(category());$('rich-fields').hidden=!rich;$('simple-fields').hidden=rich;
  $('avatar-preview').hidden=!profile.avatar;if(profile.avatar)$('avatar-preview').src='/'+profile.avatar;
  document.querySelectorAll('[data-avatar]').forEach(button=>button.classList.toggle('active',button.dataset.avatar===profile.avatar));
  $('site-preview').src='/preview/'+path('en');$('live-link').href=remoteUrl('en');
  previewMarkdown();
}
async function previewMarkdown(){if(!state)return;try{const result=await api('/api/markdown',{markdown:profile[lang].bio_markdown||''});$('markdown-preview').innerHTML=result.html||'<p>填写 Markdown 后在此预览。</p>';}catch(error){$('markdown-preview').textContent=error.message;}}
async function loadState(){const response=await fetch('/api/state');const next=await response.json();state=next;profile={...next.profiles,avatar:next.avatar,category:next.category};$('category').innerHTML=next.categories.map(item=>`<option value="${item.id}">${item.zh} / ${item.en}</option>`).join('');$('scope').textContent=next.owner?`当前账号：${next.owner} · 仅维护本人资料 · 推送到 ${next.branch}`:'首次使用请连接自己的 GitHub 账号；账号须拥有仓库 Write 权限。';$('live-link').textContent='查看测试分支 ↗';$('editing').disabled=!next.owner;dirty=false;render();}
async function connection(){if(!state)return;try{const response=await fetch('/api/connection');const info=await response.json();if(info.connected&&state.owner!==info.account){await loadState();}const login=info.login||{};connectionWaiting=login.state==='waiting';let html=info.connected?`<p>已连接：${info.account}，具有仓库写入权限。</p>`:`<p>尚未连接。当前账号：${info.account||'无'}。</p>`;if(login.state==='waiting')html+=`<p>${login.message||''}</p>${login.code?`<strong class="device-code">${login.code}</strong><p><a href="https://github.com/login/device" target="_blank" rel="noopener">打开 GitHub 授权页面 ↗</a></p>`:''}`;if(login.state==='error')html+=`<p>${login.message}</p>`;html+=`<div class="connection-actions"><button id="connect" ${!info.installed||login.state==='waiting'?'disabled':''}>${info.connected?'重新连接':'连接 GitHub'}</button><button id="check">检查连接</button></div>`;$('connection').innerHTML=html;}catch(error){$('connection').textContent=error.message;}}
async function save(){capture();if(!dirty){message('没有新的本地修改。',true);return;}const next=await api('/api/save',{revision:state.revision,profile,recruitment:null});state=next;profile={...next.profiles,avatar:next.avatar,category:next.category};dirty=false;render();$('site-preview').src='/preview/'+path(lang)+'?v='+Date.now();message('已保存并更新本地预览。',true);}
for(const language of ['en','zh'])for(const key of ['name','role','url'])$(`${language}-${key}`).addEventListener('input',()=>{profile[language][key]=$(`${language}-${key}`).value;changed();});
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>{capture();lang=button.dataset.lang;render();}));
$('category').addEventListener('change',()=>{capture();changed();render();});
$('markdown').addEventListener('input',()=>{profile[lang].bio_markdown=$('markdown').value;changed();clearTimeout(timer);timer=setTimeout(previewMarkdown,250);});
$('description').addEventListener('input',()=>{profile[lang].description=$('description').value;changed();});
$('template').addEventListener('click',()=>{const field=$('markdown'),start=field.selectionStart,end=field.selectionEnd,before=field.value.slice(0,start),after=field.value.slice(end);field.setRangeText((before&&!before.endsWith('\n')?'\n\n':'')+templates[lang]+(after&&!after.startsWith('\n')?'\n\n':''),start,end,'end');profile[lang].bio_markdown=field.value;changed();previewMarkdown();field.focus();message('模板已插入到光标位置。');});
document.querySelectorAll('[data-avatar]').forEach(button=>button.addEventListener('click',()=>{profile.avatar=button.dataset.avatar;changed();render();}));
$('avatar').addEventListener('change',async()=>{const file=$('avatar').files[0];if(!file)return;if(file.size>2500000)return message('头像最大 2.5 MB。');try{const bytes=new Uint8Array(await file.arrayBuffer());let raw='';for(let index=0;index<bytes.length;index+=8192)raw+=String.fromCharCode(...bytes.subarray(index,index+8192));profile.avatar=(await api('/api/avatar',{data:btoa(raw)})).path;changed();render();message('头像已存到本地，保存资料后即可预览。',true);}catch(error){message(error.message);}});
document.querySelectorAll('[data-preview]').forEach(button=>button.addEventListener('click',()=>{$('site-preview').src='/preview/'+path(button.dataset.preview);$('live-link').href=remoteUrl(button.dataset.preview);}));
$('save').addEventListener('click',async()=>{if(busy)return;busy=true;$('save').disabled=true;try{await save();}catch(error){message(error.message);}finally{busy=false;$('save').disabled=false;}});
$('publish').addEventListener('click',async()=>{if(busy)return;busy=true;$('publish').disabled=true;try{if(dirty)await save();const result=await api('/api/publish',{revision:state.revision});message(result.unchanged?'没有需要推送的修改。':'已推送至测试分支（正式网站不变）。提交：'+result.commit,true);}catch(error){message(error.message);}finally{busy=false;$('publish').disabled=false;}});
$('connection').addEventListener('click',async event=>{if(event.target.id==='connect'){try{await api('/api/connect',{});await connection();}catch(error){message(error.message);}}if(event.target.id==='check')await connection();});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
loadState().then(connection).catch(error=>message(error.message));setInterval(()=>{if(state&&(!state.owner||connectionWaiting))connection();},5000);
