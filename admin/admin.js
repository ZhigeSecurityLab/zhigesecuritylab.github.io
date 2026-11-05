'use strict';
let data, revision, token, backups = [], dirty = false, busy = false;
let tab = 'overview', lang = 'en', previewTimer, previewSequence = 0;
let appearanceFields = {}, publishing = null, polling = false;
const selected = {};
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[ch]));
const titles = {overview:'简介与首页',news:'News · 新闻',publications:'Publications · 论文',people:'People · 成员',recruitment:'Recruitment · 加入我们',appearance:'外观与字号',publishing:'网站发布',settings:'设置与备份'};
const descriptions = {overview:'修改当前语言的实验室名称、所属单位和简介。',news:'用 Markdown 编辑新闻；英文和中文分别维护，草稿不会显示在网站。',publications:'维护论文信息，网站会按年份自动排序。',people:'选择成员分类，维护姓名、身份与个人主页。',recruitment:'用 Markdown 维护招募对象、申请信息和邮件咨询入口。',appearance:'调整公开网站的字体、行距与 Logo 大小，中英文共用。',publishing:'连接 GitHub，发布已保存的内容与外观设置，并查看部署结果。',settings:'联系方式、成员分类、内容导出与自动备份。'};

function message(text, success = false) {
  $('message').hidden = !text;
  $('message').textContent = text;
  $('message').className = success ? 'success' : '';
}
function markDirty() {
  dirty = true;
  $('save-state').textContent = '有未保存修改';
  $('save-state').className = 'unsaved';
  renderPublishStatus();
}
function current() { return tab === 'recruitment' ? data[lang].recruitment : data[lang][tab]?.[selected[`${lang}:${tab}`] ?? 0]; }
function field(key, label, value, options = {}) {
  const attrs = options.global ? 'data-global' : options.category != null ? `data-category="${options.category}" data-key` : 'data-field';
  const labelText = escapeHTML(label);
  const control = options.textarea
    ? `<textarea ${attrs}="${key}" rows="${options.rows || 3}">${escapeHTML(value)}</textarea>`
    : `<input ${attrs}="${key}" type="${options.type || 'text'}" value="${escapeHTML(value)}">`;
  return `<label class="${options.wide ? 'wide' : ''}">${labelText}${control}</label>`;
}
function previewURL() {
  const base = '/preview/' + (lang === 'zh' ? 'zh/' : '');
  return base + (tab === 'people' ? 'people/' : $('preview-page').value);
}
function refreshPreview() {
  const url = previewURL();
  $('site-preview').src = url;
  $('site-link').href = url;
}
function renderList() {
  const list = $('record-list');
  if (!list) return;
  const items = data[lang][tab], active = selected[`${lang}:${tab}`] ?? 0;
  list.innerHTML = items.length ? items.map((item, index) => {
    const name = item.title || item.text || item.name || '未命名';
    const meta = tab === 'news' ? `${item.date} · ${item.draft ? '草稿' : '网站显示'}` : tab === 'publications' ? item.year : data.people_categories.find(g => g.id === item.category)?.[lang];
    return `<button type="button" data-index="${index}" class="${index === active ? 'active' : ''}">${escapeHTML(name)}<small>${escapeHTML(meta)}</small></button>`;
  }).join('') : '<p class="empty">还没有内容。点击上方按钮新增第一条记录。</p>';
}
function render() {
  if (!data) return;
  previewSequence++;
  $('page-title').textContent = titles[tab];
  $('page-description').textContent = descriptions[tab];
  $('languages').hidden = ['settings','publishing'].includes(tab);
  document.querySelectorAll('[data-tab]').forEach(button => button.classList.toggle('active', button.dataset.tab === tab));
  document.querySelectorAll('[data-lang]').forEach(button => button.classList.toggle('active', button.dataset.lang === lang));
  if (tab === 'overview') {
    const t = data[lang];
    $('editor').innerHTML = `<div class="card"><h2>${lang === 'en' ? '英文首页内容' : '中文首页内容'}</h2><div class="form-grid">${field('name','实验室名称',t.name)}${field('other_name','另一语言名称',t.other_name)}${field('institution','所属学校／单位（选填）',t.institution)}${field('eyebrow','页首关键词',t.eyebrow)}${field('intro','主要简介',t.intro,{textarea:true,wide:true})}${field('about','补充介绍',t.about,{textarea:true,wide:true})}</div><p class="helper">英文与中文分别维护。切换语言会保留当前修改，最后统一保存。</p></div>`;
  } else if (tab === 'recruitment') {
    const item = current();
    $('editor').innerHTML = `<section class="card"><h2>${lang === 'en' ? '英文招募信息' : '中文招募信息'}</h2><label class="checkbox"><input type="checkbox" id="recruitment-enabled" ${item.enabled ? 'checked' : ''}> 在网站显示 Recruitment／加入我们栏目</label><div class="form-grid">${field('title','栏目标题',item.title)}${field('cta_label','邮件按钮文字',item.cta_label)}${field('email_subject','邮件默认主题',item.email_subject,{wide:true})}</div><div class="toolbar"><button type="button" data-insert="bold">加粗</button><button type="button" data-insert="link">链接</button><button type="button" data-insert="list">列表</button><button type="button" data-insert="code">代码</button><label class="file-label">导入 .md<input id="import-md" type="file" accept=".md,.markdown,text/markdown,text/plain"></label><button type="button" id="export-md">导出 .md</button></div><div class="markdown-layout"><label>Markdown 正文<textarea id="markdown" data-field="body_markdown" class="markdown-input" rows="18">${escapeHTML(item.body_markdown)}</textarea></label><div><label>排版预览</label><div id="markdown-preview" class="md-preview"></div></div></div><p class="helper">邮箱按钮使用公共设置中的联系邮箱。招生名额、时间与申请流程明确后，可在正文中补充。顶部保存按钮会同时保存各语言修改。</p></section>`;
    updateMarkdown();
  } else if (tab === 'appearance') {
    $('editor').innerHTML = `<section class="card"><div class="record-top"><h2>公开网站的外观</h2><button type="button" id="reset-appearance">恢复推荐字号</button></div><div class="form-grid">${Object.entries(appearanceFields).map(([key, config]) => `<label>${escapeHTML(config.label)}${key === 'line_height' ? '' : '（px）'}<input type="number" data-appearance="${key}" min="${config.min}" max="${config.max}" step="${key === 'line_height' ? '0.1' : '1'}" value="${data.appearance?.[key] ?? config.default}"><span class="helper">范围 ${config.min}–${config.max}；推荐 ${config.default}</span></label>`).join('')}</div><p class="helper">保存后检查下方预览；手机端会自动缩小部分标题和导航，保持可读性。发布后正式网站才会更新。</p></section>`;
  } else if (tab === 'publishing') {
    $('editor').innerHTML = '<section class="card" id="connection-panel"></section><section class="note publish-note">日常流程：编辑内容或外观 → 保存并检查预览 → 点击顶部“发布到网站”。发布按钮也会先保存当前修改。每次发布只提交后台维护的内容与外观；其他人已修改远程内容时会停止，避免覆盖。</section>';
    renderConnection();
  } else if (tab === 'settings') {
    $('editor').innerHTML = `<div class="stack"><section class="card"><h2>公共设置</h2><div class="form-grid">${field('email','Contact Us 收件邮箱',data.email,{global:true,type:'email'})}${field('url','正式网站地址',data.url,{global:true,type:'url'})}${field('github','GitHub 组织地址',data.github,{global:true,type:'url',wide:true})}</div></section><section class="card"><h2>成员分类名称</h2><p class="helper">分类路径保持稳定，可修改各语言显示名称。</p>${data.people_categories.map((g,i)=>`<div class="category-row"><code>${escapeHTML(g.id)}</code>${field('en','英文名称',g.en,{category:i})}${field('zh','中文名称',g.zh,{category:i})}</div>`).join('')}</section><section class="card"><h2>备份与恢复</h2><p class="helper">每次成功保存前自动备份上一版，恢复操作前也会备份当前版本。备份仅保存在本机。</p><div class="backup-row"><label>选择备份<select id="backup">${backups.map(b=>`<option value="${escapeHTML(b)}">${escapeHTML(b)}</option>`).join('')}</select></label><button type="button" id="restore" ${backups.length ? '' : 'disabled'}>恢复此备份</button><button type="button" id="export-json">导出当前内容 JSON</button></div></section><section class="note">保存会更新本地内容文件及网站预览。确认预览后，点击顶部“发布到网站”，即可提交内容和外观设置并查看自动部署状态。首次使用请在“网站发布”中连接 GitHub。</section></div>`;
  } else {
    const item = current();
    let form = '<div class="card empty">选择左侧记录，或新增内容。</div>';
    if (item) {
      let fields = '';
      if (tab === 'news') {
        fields = `<div class="form-grid">${field('title','新闻标题',item.title ?? item.text ?? '',{wide:true})}${field('date','日期',item.date,{type:'date'})}${field('url','标题链接（选填）',item.url || '',{type:'url'})}</div><label class="checkbox"><input type="checkbox" id="published" ${item.draft ? '' : 'checked'}> 在网站显示（不勾选即保存为草稿）</label><div class="toolbar"><button type="button" data-insert="bold">加粗</button><button type="button" data-insert="link">链接</button><button type="button" data-insert="list">列表</button><button type="button" data-insert="code">代码</button><label class="file-label">导入 .md<input id="import-md" type="file" accept=".md,.markdown,text/markdown,text/plain"></label><button type="button" id="export-md">导出 .md</button></div><div class="markdown-layout"><label>Markdown 正文<textarea id="markdown" data-field="body_markdown" class="markdown-input" rows="14" placeholder="在这里输入 Markdown 正文…">${escapeHTML(item.body_markdown || '')}</textarea></label><div><label>排版预览</label><div id="markdown-preview" class="md-preview"></div></div></div><p class="helper">支持标题、加粗、链接、图片、列表、引用、表格与代码块。原始 HTML 按文字显示。顶部“保存并更新预览”会将所有修改写入文件。</p>`;
      } else if (tab === 'publications') {
        fields = `<div class="form-grid">${field('title','论文标题',item.title,{wide:true})}${field('authors','作者',item.authors,{wide:true})}${field('venue','会议／期刊',item.venue)}${field('year','年份',item.year,{type:'number'})}${field('url','论文链接（选填）',item.url || '',{wide:true,type:'url'})}</div>`;
      } else {
        fields = `<div class="form-grid">${field('name','姓名',item.name)}${field('role','身份／职务',item.role)}<label>成员分类<select data-field="category">${data.people_categories.map(g=>`<option value="${escapeHTML(g.id)}" ${g.id === item.category ? 'selected' : ''}>${escapeHTML(g[lang])}</option>`).join('')}</select></label>${field('url','个人主页（选填）',item.url || '',{type:'url'})}</div>`;
      }
      form = `<section class="card"><div class="record-top"><h2>编辑${tab === 'news' ? '新闻' : tab === 'publications' ? '论文' : '成员'}</h2><button type="button" id="delete-record" class="danger">移除此条</button></div>${fields}</section>`;
    }
    $('editor').innerHTML = `<div class="collection"><aside class="list-panel"><button type="button" id="add-record">＋ 新增${tab === 'news' ? '新闻' : tab === 'publications' ? '论文' : '成员'}</button><div id="record-list" class="record-list"></div></aside>${form}</div>`;
    renderList();
    if (tab === 'news' && item) updateMarkdown();
  }
  refreshPreview();
}
async function api(path, payload) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json','X-Editor-Token':token},body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '操作失败');
  return result;
}
async function updateMarkdown() {
  if (!['news','recruitment'].includes(tab) || !current()) return;
  const sequence = ++previewSequence;
  try {
    const result = await api('/api/markdown', {markdown:current().body_markdown || ''});
    if (sequence === previewSequence && $('markdown-preview')) {
      $('markdown-preview').innerHTML = result.html || '<p class="muted">输入 Markdown 后将在这里显示排版。</p>';
    }
  } catch (error) {
    if (sequence === previewSequence && $('markdown-preview')) $('markdown-preview').textContent = error.message;
  }
}
function loadState(result) {
  data = result.data; revision = result.revision; token = result.token; backups = result.backups; appearanceFields = result.appearance_fields || {};
  for (const language of ['en','zh']) {
    if (!data[language].recruitment) data[language].recruitment = {enabled:false,title:language === 'en' ? 'Recruitment' : '加入我们',body_markdown:'',cta_label:language === 'en' ? 'Get in touch' : '邮件咨询',email_subject:'[Zhige Lab] Research opportunity enquiry'};
  }
  dirty = false;
  $('save-state').textContent = '本地内容已保存'; $('save-state').className = '';
  $('save').disabled = false; syncPublishButton();
}
function download(name, content, mime) {
  const url = URL.createObjectURL(new Blob([content], {type:mime}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
}
document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => {tab = button.dataset.tab; message(''); render(); window.scrollTo(0,0);}));
document.querySelectorAll('[data-lang]').forEach(button => button.addEventListener('click', () => {lang = button.dataset.lang; message(''); render(); window.scrollTo(0,0);}));
$('editor').addEventListener('input', event => {
  const target = event.target;
  if (target.matches('[data-appearance]')) {data.appearance ||= {}; data.appearance[target.dataset.appearance] = Number(target.value);}
  else if (target.matches('[data-global]')) data[target.dataset.global] = target.value;
  else if (target.matches('[data-category]')) data.people_categories[Number(target.dataset.category)][target.dataset.key] = target.value;
  else if (target.id === 'published') current().draft = !target.checked;
  else if (target.id === 'recruitment-enabled') current().enabled = target.checked;
  else if (target.matches('[data-field]')) {
    const object = tab === 'overview' ? data[lang] : current();
    object[target.dataset.field] = target.dataset.field === 'year' ? Number(target.value) : target.value;
    if (target.dataset.field === 'title' && tab === 'news') delete object.text;
  } else return;
  markDirty(); renderList();
  if (target.id === 'markdown') {clearTimeout(previewTimer); previewSequence++; previewTimer = setTimeout(updateMarkdown, 250);}
});
$('editor').addEventListener('change', async event => {
  if (event.target.id !== 'import-md') return;
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 400000) return message('Markdown 文件应小于 400 KB。');
  try {
    const text = await file.text(), heading = text.match(/^#\s+(.+)\r?\n/);
    if (current().body_markdown && !confirm('导入会替换当前正文；文件含一级标题时也会更新标题。继续吗？')) return;
    if (heading) {current().title = heading[1]; current().body_markdown = text.slice(heading[0].length).trimStart();}
    else current().body_markdown = text;
    markDirty(); render(); message('Markdown 已导入。确认内容及显示状态后，点击顶部保存。', true);
  } catch (error) {message(error.message);}
});
$('editor').addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button || busy) return;
  if (button.id === 'reset-appearance') {data.appearance = {}; markDirty(); render();}
  else if (button.id === 'connect-github') {
    button.disabled = true;
    try {await api('/api/connect',{}); await pollPublishing(); message('请在 GitHub 授权页面完成连接。',true);}
    catch(error) {message(error.message);}
    finally {button.disabled=false;}
  } else if (button.id === 'check-connection') {
    button.disabled = true;
    try {await api('/api/check-connection',{}); await pollPublishing();}
    catch(error) {message(error.message);}
    finally {button.disabled=false;}
  } else if (button.dataset.index != null) {selected[`${lang}:${tab}`] = Number(button.dataset.index); render();}
  else if (button.id === 'add-record') {
    const item = tab === 'news' ? {date:localDate(),title:'',body_markdown:'',url:'',draft:true} : tab === 'publications' ? {year:new Date().getFullYear(),title:'',authors:'',venue:'',url:''} : {name:'',role:'',category:data.people_categories[0].id,url:''};
    data[lang][tab].push(item); selected[`${lang}:${tab}`] = data[lang][tab].length - 1;
    markDirty(); render();
  } else if (button.id === 'delete-record') {
    if (!confirm('从当前编辑内容中移除此条记录？保存前可重新加载页面放弃修改，保存后可从备份恢复。')) return;
    data[lang][tab].splice(selected[`${lang}:${tab}`] ?? 0, 1); selected[`${lang}:${tab}`] = 0; markDirty(); render();
  } else if (button.dataset.insert) {
    const input = $('markdown'), start = input.selectionStart, end = input.selectionEnd, chosen = input.value.slice(start,end);
    const snippets = {bold:`**${chosen || '重点内容'}**`,link:`[${chosen || '链接文字'}](https://example.org)`,list:`\n- ${chosen || '第一项'}\n- 第二项\n`,code:`\n\`\`\`\n${chosen || '代码'}\n\`\`\`\n`};
    input.setRangeText(snippets[button.dataset.insert],start,end,'end');input.dispatchEvent(new Event('input',{bubbles:true}));input.focus();
  } else if (button.id === 'export-md') {
    const item = current(); download(tab === 'recruitment' ? `recruitment-${lang}.md` : `news-${item.date}.md`, `# ${item.title || item.text || ''}\n\n${item.body_markdown || ''}\n`, 'text/markdown;charset=utf-8');
  } else if (button.id === 'export-json') {
    download('zhige-site-content.json', JSON.stringify(data,null,2)+'\n','application/json');
  } else if (button.id === 'restore') {
    if (!confirm('将用所选备份恢复全部中英文内容，并更新预览。当前未保存的修改会被替换。继续吗？')) return;
    busy = true; button.disabled = true; $('save').disabled = true;
    try {loadState(await api('/api/restore',{backup:$('backup').value,revision}));render();message('已恢复备份，并更新本地预览。',true);}
    catch(error) {message(error.message);}
    finally {busy=false;button.disabled=false;$('save').disabled=false;}
  }
});
$('save').addEventListener('click', async () => {
  if (busy) return;
  busy = true; $('save').disabled = true; $('save').textContent = '保存中…'; message('');
  $('editor').inert = true;
  try {
    const result = await api('/api/save',{data,revision});
    loadState(result);render();message('保存成功，网站预览已更新。确认效果后点击“发布到网站”。',true);
  } catch(error) {message(error.message);}
  finally {busy=false;$('editor').inert=false;$('save').disabled=false;$('save').textContent='保存并更新预览';syncPublishButton();}
});
$('refresh-preview').addEventListener('click',refreshPreview);
window.addEventListener('beforeunload', event => {if(dirty){event.preventDefault();event.returnValue='';}});
fetch('/api/state').then(response=>{if(!response.ok)throw new Error('无法加载内容');return response.json();}).then(result=>{loadState(result);render();}).catch(error=>message(error.message));

function safeGitHubLink(url, label) {
  return typeof url === 'string' && url.startsWith('https://github.com/') ? `<a href="${escapeHTML(url)}" target="_blank" rel="noopener">${label} ↗</a>` : '';
}
function renderConnection() {
  const panel = $('connection-panel');
  if (!panel) return;
  const c = publishing?.connection;
  const signature = JSON.stringify(c);
  if (panel.dataset.status === signature) return;
  panel.dataset.status = signature;
  const login = c?.login || {};
  panel.innerHTML = `<h2>GitHub 连接</h2><p>${!c ? '正在检查连接…' : c.connected ? `已连接：${escapeHTML(c.account)}，拥有实验室仓库写入权限。` : '首次使用需要授权本地 GitHub CLI；浏览器已登录可帮助完成授权。'}</p><p class="helper">目标仓库：ZhigeSecurityLab/zhigesecuritylab.github.io · main。凭据由本机 GitHub CLI 管理，不写入网站或内容文件。</p>${!c?.installed && c ? '<p>尚未安装 GitHub CLI，请按 MAINTENANCE.md 中的一次性连接步骤安装。</p>' : ''}${login.state === 'waiting' ? `<p>${escapeHTML(login.message)}</p>${login.code ? `<p class="device-code">${escapeHTML(login.code)}</p><p>${safeGitHubLink(login.url, '打开 GitHub 授权页面')}</p><p class="helper">输入上方验证码，检查页面上的账号与权限后由你完成授权。本页会自动检查连接。</p>` : ''}` : login.state === 'error' ? `<p>${escapeHTML(login.message)}</p>` : ''}<div class="toolbar"><button type="button" id="connect-github" ${!c?.installed || login.state === 'waiting' ? 'disabled' : ''}>${c?.connected ? '重新连接 GitHub' : '连接 GitHub'}</button><button type="button" id="check-connection">重新检查连接</button>${safeGitHubLink('https://github.com/ZhigeSecurityLab/zhigesecuritylab.github.io/actions','查看部署记录')}</div>`;
}
function syncPublishButton() {
  const active = ['publishing','submitted'].includes(publishing?.deployment?.state);
  $('publish').disabled = !data || busy || active;
  $('publish').textContent = active ? '发布进行中…' : '发布到网站';
}
async function pollPublishing() {
  if (polling) return;
  polling = true;
  try {
    const response = await fetch('/api/publishing');
    if (!response.ok) throw new Error('暂时无法获取发布状态');
    publishing = await response.json();
    renderPublishStatus();
    renderConnection(); syncPublishButton();
  } catch(error) {
    if (tab === 'publishing' && $('connection-panel')) $('connection-panel').textContent = error.message;
  } finally {polling=false;}
}
$('publish').addEventListener('click', async () => {
  if (busy) return;
  busy=true; syncPublishButton(); $('save').disabled=true; $('editor').inert=true; message('');
  try {
    if (dirty) {loadState(await api('/api/save',{data,revision})); render();}
    if (!publishing?.connection?.connected) {
      tab='publishing'; render(); message('内容已保存在本地。请先连接 GitHub，再点击“发布到网站”。'); return;
    }
    await api('/api/publish',{revision});
    await pollPublishing();
  } catch(error) {message(error.message);}
  finally {busy=false;$('editor').inert=false;$('save').disabled=false;syncPublishButton();}
});
async function publishingLoop() {await pollPublishing(); setTimeout(publishingLoop,4000);}
publishingLoop();

$('preview-page').addEventListener('change',refreshPreview);
$('preview-width').addEventListener('change',()=>{$('site-preview').classList.toggle('mobile-preview',$('preview-width').value==='mobile');});

function renderPublishStatus() {
  const d = publishing?.deployment;
  if (!d) return;
  const panel = $('publishing-status');
  const unpublished = dirty || (d.revision && revision && d.revision !== revision);
  const signature = JSON.stringify([d,unpublished]);
  if (panel.dataset.status === signature) return;
  panel.dataset.status = signature;
  panel.hidden = d.state === 'idle';
  panel.className = 'publish-status ' + (d.state === 'success' ? 'success' : ['error','deploy_error'].includes(d.state) ? 'error' : '');
  panel.innerHTML = `<strong>${escapeHTML(d.message)}</strong>${unpublished && d.commit ? '<p>当前本地还有尚未发布的修改。</p>' : ''}<div class="publish-links">${safeGitHubLink(d.commit_url,'查看提交')}${safeGitHubLink(d.run_url,'查看部署日志')}${d.state === 'success' ? '<a href="https://zhigesecuritylab.github.io/" target="_blank" rel="noopener">打开正式网站 ↗</a>' : ''}</div>`;
}
