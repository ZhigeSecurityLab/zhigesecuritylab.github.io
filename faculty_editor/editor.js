'use strict';
let works=[], orcid='', state, profile, recruitment, facultyLang='en', recruitmentLang='en';
let profileDirty=false, recruitmentDirty=false, busy=false, previewTimer, connectionWaiting=false;
const $=id=>document.getElementById(id);
const templates={
  en:'## Biography\n\nWrite a short introduction.\n\n## Research Interests\n\n- Research topic 1\n- Research topic 2\n\n## Selected Publications\n\n- Add representative publications with links.\n\n## Projects and Service\n\nDescribe projects, awards, or academic service if relevant.\n\n## Contact\n\nAdd a public contact method if desired.\n',
  zh:'## 个人简介\n\n在这里填写简短介绍。\n\n## 研究方向\n\n- 研究方向一\n- 研究方向二\n\n## 代表性论文\n\n- 添加论文及链接。\n\n## 项目与学术服务\n\n根据需要填写项目、荣誉或学术服务。\n\n## 联系方式\n\n根据需要填写公开联系方式。\n'
};
function message(text,ok=false){$('message').textContent=text;$('message').className=ok?'success':'';}
function modified(section){if(section==='profile')profileDirty=true;else recruitmentDirty=true;message('有尚未保存的修改。');}
async function api(path,payload){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Editor-Token':state.token},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error||'操作失败');return data;}
function captureFaculty(){if(!profile)return;for(const lang of ['en','zh']){profile[lang].orcid=orcid;profile[lang].publications=structuredClone(works);}profile[facultyLang].bio_markdown=$('markdown').value;}
function captureRecruitment(){if(!recruitment)return;const item=recruitment[recruitmentLang];item.enabled=$('recruitment-enabled').checked;item.title=$('recruitment-title').value;item.cta_label=$('recruitment-cta').value;item.email_subject=$('recruitment-subject').value;item.body_markdown=$('recruitment-markdown').value;}
function renderFaculty(){for(const lang of ['en','zh'])for(const key of ['name','role','url'])$(`${lang}-${key}`).value=profile[lang][key]||'';$('markdown').value=profile[facultyLang].bio_markdown||'';document.querySelectorAll('[data-lang]').forEach(button=>button.classList.toggle('active',button.dataset.lang===facultyLang));$('avatar-preview').hidden=!profile.avatar;$('avatar-empty').hidden=!!profile.avatar;if(profile.avatar)$('avatar-preview').src='/'+profile.avatar;document.querySelectorAll('[data-avatar]').forEach(button=>button.classList.toggle('active',button.dataset.avatar===profile.avatar));previewMarkdown('faculty');}
function renderRecruitment(){const item=recruitment[recruitmentLang];$('recruitment-enabled').checked=item.enabled;$('recruitment-title').value=item.title||'';$('recruitment-cta').value=item.cta_label||'';$('recruitment-subject').value=item.email_subject||'';$('recruitment-markdown').value=item.body_markdown||'';document.querySelectorAll('[data-recruitment-lang]').forEach(button=>button.classList.toggle('active',button.dataset.recruitmentLang===recruitmentLang));previewMarkdown('recruitment');}
async function previewMarkdown(section){if(!state)return;const body=section==='faculty'?profile[facultyLang].bio_markdown:recruitment[recruitmentLang].body_markdown;const target=section==='faculty'?'markdown-preview':'recruitment-preview';try{const result=await api('/api/markdown',{markdown:body||''});$(target).innerHTML=result.html||'<p>填写 Markdown 后在此预览。</p>';}catch(error){$(target).textContent=error.message;}}
async function connection(){if(!state)return;try{const r=await fetch('/api/connection');const c=await r.json();const login=c.login||{};connectionWaiting=login.state==='waiting';let html=c.connected?`<p>已连接：${c.account}，具备仓库写入权限。</p>`:`<p>尚未连接 ${state.owner}。当前账号：${c.account||'无'}。</p>`;if(login.state==='waiting')html+=`<p>${login.message||''}</p>${login.code?`<span class="device-code">${login.code}</span><p><a href="https://github.com/login/device" target="_blank" rel="noopener">打开 GitHub 授权页面 ↗</a></p>`:''}`;if(login.state==='error')html+=`<p>${login.message}</p>`;html+=`<div class="connection-actions"><button id="connect" ${!c.installed||login.state==='waiting'?'disabled':''}>${c.connected?'重新连接':'连接 GitHub'}</button><button id="check">检查连接</button></div>`;$('connection').innerHTML=html;}catch(error){$('connection').textContent=error.message;}}
async function save(){captureFaculty();captureRecruitment();if(!profileDirty&&!recruitmentDirty){message('没有新的本地修改。',true);return;}const next=await api('/api/save',{revision:state.revision,profile:profileDirty?profile:null,recruitment:recruitmentDirty?recruitment:null});state=next;works=structuredClone(next.publications||[]);orcid=next.orcid||'';renderPapers();profile={...next.profiles,avatar:next.avatar};recruitment=structuredClone(next.recruitment);profileDirty=false;recruitmentDirty=false;renderFaculty();renderRecruitment();$('site-preview').src=$('site-preview').src.split('?')[0]+'?v='+Date.now();message('已保存并更新本地预览。',true);}
function previewPath(kind){if(kind==='publications')return 'publications/';if(kind==='en')return 'people/faculty/';if(kind==='zh')return 'zh/people/faculty/';if(kind==='recruitment-en')return 'recruitment/';return 'zh/recruitment/';}
document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',()=>{captureFaculty();facultyLang=button.dataset.lang;renderFaculty();}));
document.querySelectorAll('[data-recruitment-lang]').forEach(button=>button.addEventListener('click',()=>{captureRecruitment();recruitmentLang=button.dataset.recruitmentLang;renderRecruitment();}));
document.querySelectorAll('[data-preview]').forEach(button=>button.addEventListener('click',()=>{const path=previewPath(button.dataset.preview);$('site-preview').src='/preview/'+path;if(state.branch==='main')$('live-link').href='https://zhigesecuritylab.github.io/'+path;}));
for(const lang of ['en','zh'])for(const key of ['name','role','url'])$(`${lang}-${key}`).addEventListener('input',()=>{profile[lang][key]=$(`${lang}-${key}`).value;modified('profile');});
$('markdown').addEventListener('input',()=>{profile[facultyLang].bio_markdown=$('markdown').value;modified('profile');clearTimeout(previewTimer);previewTimer=setTimeout(()=>previewMarkdown('faculty'),250);});
$('template').addEventListener('click',()=>{const field=$('markdown');const start=field.selectionStart,end=field.selectionEnd;const before=field.value.slice(0,start),after=field.value.slice(end);const insertion=(before&&!before.endsWith('\n')?'\n\n':'')+templates[facultyLang]+(after&&!after.startsWith('\n')?'\n\n':'');field.setRangeText(insertion,start,end,'end');profile[facultyLang].bio_markdown=field.value;modified('profile');previewMarkdown('faculty');field.focus();message('模板已插入到光标位置，可直接修改。');});
$('avatar').addEventListener('change',async()=>{const file=$('avatar').files[0];if(!file)return;if(file.size>2500000)return message('头像最大 2.5 MB。');try{const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));profile.avatar=(await api('/api/avatar',{data:btoa(binary)})).path;modified('profile');renderFaculty();message('头像已上传到本地；保存并推送后才会公开。',true);}catch(error){message(error.message);}});
document.querySelectorAll('[data-avatar]').forEach(button=>button.addEventListener('click',()=>{profile.avatar=button.dataset.avatar;modified('profile');renderFaculty();}));
for(const id of ['recruitment-enabled','recruitment-title','recruitment-cta','recruitment-subject'])$(id).addEventListener('input',()=>{captureRecruitment();modified('recruitment');});
$('recruitment-markdown').addEventListener('input',()=>{captureRecruitment();modified('recruitment');clearTimeout(previewTimer);previewTimer=setTimeout(()=>previewMarkdown('recruitment'),250);});
$('save').addEventListener('click',async()=>{if(busy)return;busy=true;$('save').disabled=true;try{await save();}catch(error){message(error.message);}finally{busy=false;$('save').disabled=false;}});
$('publish').addEventListener('click',async()=>{if(busy)return;busy=true;$('publish').disabled=true;try{if(profileDirty||recruitmentDirty)await save();const result=await api('/api/publish',{revision:state.revision});if(result.unchanged)message('没有需要推送的修改。',true);else{message(state.branch==='main'?'已推送 GitHub，网站正在自动部署。提交：'+result.commit:'已推送到测试分支，正式网站不会变化。提交：'+result.commit,true);if(state.branch!=='main'){$('live-link').href=result.url;$('live-link').textContent='查看测试提交 ↗';}}}catch(error){message(error.message);}finally{busy=false;$('publish').disabled=false;}});
$('connection').addEventListener('click',async event=>{if(event.target.id==='connect'){try{await api('/api/connect',{});await connection();}catch(error){message(error.message);}}if(event.target.id==='check')await connection();});
window.addEventListener('beforeunload',event=>{if(profileDirty||recruitmentDirty){event.preventDefault();event.returnValue='';}});
fetch('/api/state').then(r=>r.json()).then(result=>{state=result;profile={...result.profiles,avatar:result.avatar};recruitment=structuredClone(result.recruitment);$('sync-status').textContent=result.sync?.message||'已载入本地资料';$('sync-official').hidden=result.branch!=='main';$('editor-scope').textContent=`当前账号：${state.owner} · 目标分支：${state.branch} · 仅编辑本人 Faculty、Publications 与 Recruitment`;$('publish-hint').textContent=state.branch==='main'?'首次发布请用 garrisongys 连接 GitHub；只合并其 Faculty 资料和中英文 Recruitment。':'测试模式：请用 zhengfeiLian 授权；仅推送当前测试分支，正式网站不会变化。';if(state.branch!=='main'){$('live-link').hidden=true;}orcid=result.orcid||'';works=structuredClone(result.publications||[]);$('orcid').value=orcid;renderPapers();renderFaculty();renderRecruitment();connection();}).catch(error=>message(error.message));
setInterval(()=>{if(connectionWaiting)connection();},5000);

function paperField(label, value, update, multiline=false){
  const wrap=document.createElement('label');wrap.textContent=label;
  const input=document.createElement(multiline?'textarea':'input');input.value=value||'';if(multiline)input.rows=5;
  input.addEventListener('input',()=>{update(input.value);modified('profile');});wrap.append(input);return wrap;
}
function renderPapers(){
  const query=$('paper-search').value.toLowerCase();const root=$('papers');root.replaceChildren();
  const filtered=works.filter(p=>`${p.title} ${p.authors} ${p.year}`.toLowerCase().includes(query));
  for(const kind of ['conference','journal','other']){
    const group=filtered.filter(p=>p.kind===kind).sort((a,b)=>['A','B','C','Unrated'].indexOf(a.tier)-['A','B','C','Unrated'].indexOf(b.tier)||b.year-a.year);
    if(!group.length)continue;
    const heading=document.createElement('h3');heading.textContent={conference:'会议论文',journal:'期刊论文',other:'其他成果'}[kind];root.append(heading);
    for(const p of group){
      const details=document.createElement('details');details.className='paper-card';const summary=document.createElement('summary');
      const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=p.selected;
      checkbox.addEventListener('click',e=>e.stopPropagation());checkbox.addEventListener('change',async()=>{p.selected=checkbox.checked;modified('profile');if(p.selected&&(!p.bibtex||!p.pdf_url)){checkbox.disabled=true;try{Object.assign(p,await api('/api/publication',{publication:p}));modified('profile');renderPapers();}catch(error){message(error.message);}finally{checkbox.disabled=false;}}});
      const title=document.createElement('span');title.textContent=` ${p.year} · ${p.title} · ${p.tier}`;summary.append(checkbox,title);details.append(summary);
      const rank=document.createElement('p');rank.textContent=`CCF 自动匹配：${p.tier==='Unrated'?'待核验':p.tier} · ${p.ccf_edition||'2026 第七版'}。修改会议或期刊后保存将重新匹配。`;details.append(rank);const grid=document.createElement('div');grid.className='columns';
      for(const [key,label,choices] of [['kind','类型',[['conference','会议'],['journal','期刊'],['other','其他']]]]){
        const labelEl=document.createElement('label');labelEl.textContent=label;const select=document.createElement('select');for(const [value,text] of choices){const option=new Option(text,value);select.add(option);}select.value=p[key];select.addEventListener('change',()=>{p[key]=select.value;modified('profile');renderPapers();});labelEl.append(select);grid.append(labelEl);
      }
      for(const [key,label] of [['title','论文标题'],['authors','作者'],['venue','会议／期刊'],['year','年份'],['doi','DOI（选填）'],['url','论文页面链接'],['pdf_url','PDF 链接（可补充）']])grid.append(paperField(label,p[key],value=>p[key]=key==='year'?Number(value):value));
      if(p.bibtex_source){const note=document.createElement('p');note.className='hint';note.textContent='此 BibTeX 根据公开元数据生成，请核对作者与字段。';details.append(note);}details.append(grid,paperField('BibTeX（支持编辑与复制）',p.bibtex,value=>p.bibtex=value,true));
      const enrich=document.createElement('button');enrich.type='button';enrich.textContent='获取／补全 BibTeX、PDF 与元数据';enrich.addEventListener('click',async()=>{enrich.disabled=true;try{Object.assign(p,await api('/api/publication',{publication:p}));modified('profile');renderPapers();message(p.pdf_url&&p.bibtex?'已获取，可检查后保存。':'已尝试获取；缺失内容可手工补充。',true);}catch(error){message(error.message);}finally{enrich.disabled=false;}});details.append(enrich);root.append(details);
    }
  }
  if(!filtered.length)root.textContent=works.length?'没有匹配的论文。':'尚未同步论文。';
}
$('orcid').addEventListener('input',()=>{orcid=$('orcid').value.trim();modified('profile');});
$('paper-search').addEventListener('input',renderPapers);
$('orcid-sync').addEventListener('click',async()=>{
  const button=$('orcid-sync');button.disabled=true;$('orcid-status').textContent='正在读取 ORCID 公开成果与详情，可能需要一分钟…';
  try{
    const result=await api('/api/orcid',{orcid:$('orcid').value});
    orcid=result.orcid;$('orcid').value=orcid;
    const existing=new Map(works.map(p=>[p.id,p]));let added=0;
    for(const paper of result.works){if(!existing.has(paper.id)){works.push(paper);added++;}else{const previous=existing.get(paper.id);for(const field of ['tier','ccf_edition','ccf_source','ccf_status','ccf_venue','ccf_page'])previous[field]=paper[field];}}
    modified('profile');renderPapers();$('orcid-status').textContent=`公开记录姓名：${result.name||'未公开'}。读取 ${result.works.length} 条，新增 ${added} 条，当前共 ${works.length} 条。请核对身份后勾选。${result.warning||''}`;
  }catch(error){$('orcid-status').textContent=error.message;}finally{button.disabled=false;}
});

let searchResults=[];
$('paper-title-query').value='';$('paper-search-results').replaceChildren();$('paper-search-status').textContent='';$('paper-search-add').hidden=true;
function duplicatePaper(a,b){if(a.kind!==b.kind)return false;if(a.doi&&b.doi)return a.doi.toLowerCase()===b.doi.toLowerCase();const k=x=>x.toLowerCase().replace(/[^a-z0-9]/g,'');return k(a.title)&&k(a.title)===k(b.title);}
$('paper-title-search').addEventListener('click',async()=>{
 const button=$('paper-title-search');button.disabled=true;$('paper-search-status').textContent='正在查询 USENIX 官方、Crossref、arXiv 与 OpenAlex…';$('paper-search-results').replaceChildren();$('paper-search-add').hidden=true;
 try{const result=await api('/api/paper-search',{title:$('paper-title-query').value});searchResults=result.results.map(p=>({...p,add:false}));
 for(const p of searchResults){const label=document.createElement('label');label.className='paper-card';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.addEventListener('change',()=>p.add=checkbox.checked);const text=document.createElement('span');text.textContent=` ${p.title} · ${p.year} · ${p.authors} · ${p.venue||'场所待补充'} · ${p.search_source}${p.award?' · '+p.award:''} · 标题相似度 ${p.title_similarity}% · ${p.pdf_url?'有 PDF 链接':'PDF 待补充'} · ${p.tier==='Unrated'?'CCF 待核验':'CCF '+p.tier}`;label.append(checkbox,text);if(/^https?:\/\//.test(p.url)){const source=document.createElement('a');source.href=p.url;source.target='_blank';source.rel='noopener';source.textContent=' 查看来源 ↗';source.addEventListener('click',e=>e.stopPropagation());label.append(source);}$('paper-search-results').append(label);}
 $('paper-search-status').textContent=`找到 ${searchResults.length} 个候选，请核对作者与版本。${result.warning||''}`;$('paper-search-add').hidden=!searchResults.length;
 }catch(error){$('paper-search-status').textContent=error.message;}finally{button.disabled=false;}
});
$('paper-search-add').addEventListener('click',async()=>{
 const button=$('paper-search-add');button.disabled=true;let added=0,duplicates=0;
 try{for(const candidate of searchResults.filter(p=>p.add)){if(works.some(p=>duplicatePaper(p,candidate))){duplicates++;continue;}const p=structuredClone(candidate);delete p.add;p.selected=true;try{Object.assign(p,await api('/api/publication',{publication:p}));}catch(error){message('已保留检索元数据，可稍后重试补全。');}works.push(p);added++;}
 if(added){modified('profile');$('paper-search').value='';renderPapers();}$('paper-search-status').textContent=`已添加 ${added} 条，跳过重复 ${duplicates} 条。新增论文已勾选展示，保存预览后再推送。`;
 }finally{button.disabled=false;}
});
$('paper-blank').addEventListener('click',()=>{const p={id:'manual:'+Date.now()+'-'+Math.random().toString(36).slice(2),title:'待填写论文标题',authors:'',venue:'',year:new Date().getFullYear(),kind:'other',tier:'Unrated',doi:'',url:'',pdf_url:'',bibtex:'',selected:false};works.push(p);$('paper-search').value=p.title;modified('profile');renderPapers();message('已添加空白条目，请展开填写并勾选展示。');});

$('sync-official').addEventListener('click',async()=>{
 if(profileDirty||recruitmentDirty)return message('请先保存当前编辑，再重新读取；已保存资料会自动备份。');
 const button=$('sync-official');button.disabled=true;
 try{const next=await api('/api/sync',{revision:state.revision});state=next;profile={...next.profiles,avatar:next.avatar};recruitment=structuredClone(next.recruitment);orcid=next.orcid||'';works=structuredClone(next.publications||[]);$('orcid').value=orcid;$('sync-status').textContent=next.sync.message;renderFaculty();renderRecruitment();renderPapers();$('site-preview').src='/preview/people/faculty/?v='+Date.now();message(next.sync.state==='synced'?'正式资料已同步。':next.sync.message,next.sync.state==='synced');}catch(error){message(error.message);}finally{button.disabled=false;}
});
