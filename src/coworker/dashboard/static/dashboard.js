const API = '/api';
let currentView = 'overview';
let viewHistory = [];

async function fetchJSON(url) { const r=await fetch(url); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
function $(s) { return document.querySelector(s); }
function $$(s) { return document.querySelectorAll(s); }

function renderNav() {
  const items = SUBNAV[currentTab];
  let html = '<div class="sidebar-header"><span class="icon">◆</span> Coworker</div><div class="subnav">';
  items.forEach(i => {
    const a = i.id === currentView ? ' active' : '';
    html += '<div class="subnav-item' + a + '" onclick="navigate(\'' + i.id + '\')"><span class="icon">' + i.icon + '</span> ' + i.label;
    if (i.toggle) html += '<span class="subnav-toggle">Hotspots</span>';
    html += '</div>';
  });
  html += '</div>';
  $('#sidebar').innerHTML = html;
  document.querySelectorAll('#topbar-tabs .tab').forEach(t => t.classList.toggle('active', t.dataset.tab === currentTab));
}

function navigate(view, ph) {
  if (ph !== false && currentView !== view) viewHistory.push(currentView);
  currentView = view;
  for (const [tid, items] of Object.entries(SUBNAV)) {
    if (items.find(i => i.id === view)) { currentTab = tid; break; }
  }
  renderNav();
  $('#main').innerHTML = '<div class="content">' + skForView(currentView) + '</div>';
  const fn = LOAD_MAP[view] || loadOverview;
  safeLoad(fn)().then(enrichContent);
}
function goBack(){const p=viewHistory.pop();if(p)navigate(p,false);}
function timeAgo(ts){if(!ts)return'-';const m=Math.floor((Date.now()-new Date(ts).getTime())/60000);if(m<1)return'now';if(m<60)return m+'m';const h=Math.floor(m/60);return h<24?h+'h':Math.floor(h/24)+'d';}
function fmtTime(ts){if(!ts)return'-';const d=new Date(ts);const p=n=>String(n).padStart(2,'0');return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds());}
function fmtNum(n){return(n||0).toLocaleString();}
function fmtModel(m){if(!m)return'-';if(typeof m==='string'){try{const p=JSON.parse(m);if(typeof p==='object')return p.id||p.modelID||JSON.stringify(p).slice(0,40);}catch(e){}}if(typeof m==='object')return m.id||m.modelID||JSON.stringify(m).slice(0,40);return String(m).slice(0,40);}
function shortId(id,l){return(id||'').slice(0,l||20);}
function trunc(s,l){s=s||'';return s.length>(l||80)?s.slice(0,l||80)+'…':s;}
function ideTags(ides){if(!ides)return'';const m={};Object.entries(ides).forEach(([i,c])=>{const l=/claude/i.test(i)?'claude':/opencode/i.test(i)?'opencode':/gemini/i.test(i)?'gemini':i;m[l]=(m[l]||0)+c;});const cl={claude:{cls:'tag-ide-claude',icon:'<svg class="ide-icon" viewBox="0 0 16 16" width="12" height="12"><path d="M8 0L10 6 16 8 10 10 8 16 6 10 0 8 6 6Z" fill="currentColor"/></svg>',label:'Claude Code'},opencode:{cls:'tag-ide-opencode',icon:'<svg class="ide-icon" viewBox="0 0 16 16" width="12" height="12"><path d="M8 1L14 7 8 15 2 7Z" fill="currentColor"/></svg>',label:'OpenCode'},gemini:{cls:'tag-ide-gemini',icon:'<svg class="ide-icon" viewBox="0 0 16 16" width="12" height="12"><path d="M8 2Q8 8 14 8Q8 8 8 14Q8 8 2 8Q8 8 8 2Z" fill="currentColor"/></svg>',label:'Gemini'}};return Object.entries(m).sort((a,b)=>b[1]-a[1]).map(([l,c])=>{const info=cl[l]||{cls:'tag-tool',icon:'',label:l};return' <span class="tag '+info.cls+'">'+info.icon+' '+info.label+' '+c+'</span>';}).join('');}
function ideIconHtml(ide){
  if(!ide)return '<span class="tag tag-tool">-</span>';
  const i=ide.toLowerCase();
  if(i.includes('claude'))return '<span class="tag tag-ide-claude"><svg class="ide-icon" viewBox="0 0 16 16" width="14" height="14"><path d="M8 0L10 6 16 8 10 10 8 16 6 10 0 8 6 6Z" fill="currentColor"/></svg> Claude Code</span>';
  if(i.includes('opencode'))return '<span class="tag tag-ide-opencode"><svg class="ide-icon" viewBox="0 0 16 16" width="14" height="14"><path d="M8 1L14 7 8 15 2 7Z" fill="currentColor"/></svg> OpenCode</span>';
  if(i.includes('gemini'))return '<span class="tag tag-ide-gemini"><svg class="ide-icon" viewBox="0 0 16 16" width="14" height="14"><path d="M8 2Q8 8 14 8Q8 8 8 14Q8 8 2 8Q8 8 8 2Z" fill="currentColor"/></svg> Gemini</span>';
  return '<span class="tag tag-tool">'+escHtml(ide)+'</span>';
}
function escHtml(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function escId(s){return(s||'').replace(/[^a-zA-Z0-9_-]/g,'_');}
function expRow(c,d,sid){const id='e'+Math.random().toString(36).slice(2,8);return'<tr class="exp-row" onclick="toggleExp(\''+id+'\',\''+(sid||'')+'\')" style="cursor:pointer">'+c+'<td style="width:30px;text-align:center"><span id="'+id+'-i">▶</span></td></tr><tr id="'+id+'" style="display:none"><td colspan="12" style="padding:0"><div style="padding:14px 18px;background:var(--bg-tertiary);border-bottom:1px solid var(--border)" id="'+id+'-c">'+d+'</div></td></tr>';}
function toggleExp(id,sid){
  const r=document.getElementById(id),i=document.getElementById(id+'-i');if(!r)return;
  const s=r.style.display==='none';r.style.display=s?'table-row':'none';if(i)i.textContent=s?'▼':'▶';
  if(s&&sid)loadSessionExpand(id,sid);
}
async function loadSessionExpand(id,sid){
  const c=document.getElementById(id+'-c');if(!c||c.dataset.loaded)return;c.dataset.loaded='1';
  c.innerHTML='<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading...</span></div>';

  // Shared session table renderer
  function renderSessionTable(sessions, maxRows, label){
    if(!sessions||sessions.length===0)return'<div class="text-sm text-muted" style="padding:20px;text-align:center">No sessions</div>';
    const slice=sessions.slice(0,maxRows||30);
    let html='<div class="text-xs text-muted mb-sm" style="padding:4px 0">'+(label||sessions.length+' sessions')+'</div><table style="width:100%"><tr><th>ID</th><th>IDE</th><th>Project</th><th>Initiative</th><th class="text-right">Msgs</th><th class="text-right">Tools</th><th>Started</th></tr>';
    slice.forEach(s=>{
      html+=`<tr style="cursor:pointer" onclick="viewSession('${s.id}')"><td class="text-monospace text-xs">${shortId(s.id,20)}</td><td>${ideIconHtml(s.ide)}</td><td class="text-xs">${s.project||'-'}</td><td>${s.initiative?`<span class="tag tag-session" style="font-size:9px">${s.initiative}</span>`:'-'}</td><td class="text-right">${s.message_count||0}</td><td class="text-right">${s.tool_count||0}</td><td class="text-xs text-muted">${fmtTime(s.created_at)}</td></tr>`;
    });
    html+='</table>';
    if(sessions.length>maxRows)html+=`<div class="text-xs text-muted" style="padding:8px;text-align:center">… and ${sessions.length-maxRows} more</div>`;
    return html;
  }

  // Handle project expand (prefix "project:")
  if(sid.startsWith('project:')){
    const pn=sid.slice(8);
    try{
      const sessions=await fetchJSON(API+'/sessions?limit=500');
      const projSessions=sessions.filter(s=>{
        if(pn==='root')return !s.project||s.project===''||s.project==='root';
        const sp=(s.project||s.cwd||'').toLowerCase();
        return sp.includes(pn)||sp.replace(/.*\//,'').includes(pn);
      });
      c.innerHTML=renderSessionTable(projSessions,30);
    }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
    return;
  }

  // Handle skill expand (prefix "skill:")
  if(sid.startsWith('skill:')){
    const sn=sid.slice(6);
    try{
      const [sessions,detail,skillsData,sessionIds,mentions]=await Promise.all([
        fetchJSON(API+'/sessions?limit=500'),
        fetchJSON(API+'/skill-detail?name='+encodeURIComponent(sn)+'&days=3650'),
        fetchJSON(API+'/skills'),
        fetchJSON(API+'/skill-session-ids?name='+encodeURIComponent(sn)).catch(()=>[]),
        fetchJSON(API+'/skill-mentions?name='+encodeURIComponent(sn)).catch(()=>[])
      ]);
      // Find total_calls for this skill
      const skillMeta=skillsData.find(s=>s.name===sn);
      const totalCalls=skillMeta?.total_calls||0;
      // Collect unique session IDs from all sources
      const allSids=new Set();
      detail.forEach(d=>allSids.add(d.session_id));
      sessionIds.forEach(id=>allSids.add(id));
      const mentionSids=new Set(mentions);
      // Legacy check: if skill has calls from old JSONL but no detailed records
      const legacyCalls=totalCalls-allSids.size;
      const filtered=sessions.filter(s=>allSids.has(s.id));
      const mentionedSessions=sessions.filter(s=>mentionSids.has(s.id)&&!allSids.has(s.id));
      let html='<div class="panel" style="padding:8px 14px;margin-bottom:12px"><div class="flex" style="flex-wrap:wrap;gap:0">';
      html+=`<span class="stat-inline"><span class="label">Calls</span> <span class="value red">${totalCalls}</span></span>`;
      html+=`<span class="stat-inline"><span class="label">Sessions</span> <span class="value blue">${filtered.length}</span></span>`;
      if(mentionedSessions.length>0)html+=`<span class="stat-inline"><span class="label">Mentioned</span> <span class="value yellow">${mentionedSessions.length}</span></span>`;
      html+=`<span class="stat-inline"><span class="label">Records</span> <span class="value cyan">${detail.length}</span></span>`;
      html+='</div></div>';
      if(legacyCalls>0&&filtered.length===0){
        html+=`<div class="panel mb-md"><div class="panel-body" style="padding:12px 16px"><div class="text-sm text-muted">⚡ This skill was used <strong>${totalCalls} times</strong> in legacy sessions (June 2026). The original session data was not preserved by the old import pipeline.</div></div>`;
        if(mentionedSessions.length>0){
          html+=renderSessionTable(mentionedSessions,30,mentionedSessions.length+' sessions (mentioned in tool output)');
        }
        html+='</div>';
      }else if(filtered.length>0){
        html+=renderSessionTable(filtered,30);
        if(mentionedSessions.length>0){
          html+=`<div class="panel mt-md"><div class="panel-header">Also Mentioned <span class="count">${mentionedSessions.length} sessions</span></div>`;
          html+=renderSessionTable(mentionedSessions,10);
          html+=`</div>`;
        }
      }else{
        html+=`<div class="text-sm text-muted" style="padding:20px;text-align:center">${totalCalls>0?'Used '+totalCalls+' times in legacy sessions (detailed data not available)':'Installed but never used'}</div>`;
      }
      if(detail.length>0){
        html+='<div class="panel mt-md"><div class="panel-header">Call History <span class="count">'+detail.length+' calls</span></div><div class="panel-body" style="max-height:300px;overflow-y:auto;padding:0">';
        detail.slice(0,50).forEach(d=>{
          html+=`<div class="timeline-item" style="padding:4px 14px"><div class="timeline-icon">⚡</div><div><span class="tag tag-skill">${sn}</span></div><div class="timeline-content"><span class="text-xs text-muted">${d.session_id||''}</span></div><div class="timeline-time text-xs text-muted">${(d.ts||'').slice(11,19)}</div></div>`;
        });
        html+='</div></div>';
      }
      c.innerHTML=html;
    }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
    return;
  }

  // Handle tool expand (prefix "tool:")
  if(sid.startsWith('tool:')){
    const tn=sid.slice(5);
    try{
      const [sessions,detail]=await Promise.all([fetchJSON(API+'/sessions?limit=500'),fetchJSON(API+'/tool-detail?tool='+encodeURIComponent(tn))]);
      const sids=new Set(detail.map(d=>d.session_id));
      const filtered=sessions.filter(s=>sids.has(s.id));
      c.innerHTML=renderSessionTable(filtered,30);
    }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
    return;
  }

  // Handle initiative expand (prefix "initiative:")
  if(sid.startsWith('initiative:')){
    const initName=sid.slice(11);
    try{
      const sessions=await fetchJSON(API+'/sessions?limit=500');
      const filtered=sessions.filter(s=>s.initiative===initName);
      c.innerHTML=renderSessionTable(filtered,30);
    }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
    return;
  }

  // Handle knowledge expand (prefix "knowledge:")
  if(sid.startsWith('knowledge:')){
    const kid=sid.slice(9);
    await _loadKnowledgeSessions(id, kid);
    return;
  }

  // Normal session expand
  try{
    const[det,time]=await Promise.all([fetchJSON(API+'/sessions/'+sid),fetchJSON(API+'/sessions/'+sid+'/timeline').catch(()=>[])]);
    const s=det.session,sum=det.summary,msgs=det.messages||[],tools=det.tool_calls||[],files=det.file_ops||[];
    const toolCnt={};tools.forEach(t=>{toolCnt[t.tool]=(toolCnt[t.tool]||0)+1;});
    const skillCalls=tools.filter(t=>t.tool==='Skill').length;
    const turns=msgs.filter(m=>m.type==='user').length;
    let html='<div class="grid-3 mb-md" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))">';
    html+=`<div class="summary-card"><div class="label">IDE</div><div class="text" style="font-size:13px">${s?.ide||'-'}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Project</div><div class="text">${s?.project||'(root)'}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Turns</div><div class="text">${turns} (${msgs.length} msgs)</div></div>`;
    html+=`<div class="summary-card"><div class="label">Skill Calls</div><div class="text" style="color:var(--red)">${skillCalls}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Tool Calls</div><div class="text" style="color:var(--green)">${tools.length}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Files</div><div class="text" style="color:var(--blue)">${files.length}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Duration</div><div class="text">${det.stats?.duration_min?det.stats.duration_min+'m':'-'}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Model</div><div class="text">${s?.model?JSON.stringify(s.model).slice(0,30):'-'}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Initiative</div><div class="text">${s?.initiative||'-'}</div></div>`;
    html+=`<div class="summary-card"><div class="label">Branch</div><div class="text text-monospace text-xs">${s?.branch||'-'}</div></div>`;
    if(sum?.efficiency_score!=null)html+=`<div class="summary-card"><div class="label">Efficiency</div><div class="text" style="color:${sum.efficiency_score>0.6?'var(--green)':'var(--yellow)'}">${Math.round(sum.efficiency_score*100)}%</div></div>`;
    html+='</div>';
    // Flow diagram
    let steps=[];
    if(sum?.sop_workflows)steps=sum.sop_workflows.split(/[→|]/).map(s=>s.trim()).filter(Boolean);
    else{tools.slice(0,15).forEach(t=>{const n=t.parent_skill||t.tool;if(!steps.includes(n))steps.push(n);});}
    if(steps.length===0)steps=['No steps recorded'];
    const bw=140,bh=38,bg=10;
    const svgW=Math.max(300,steps.length*(bw+bg)+30);
    html+=`<div class="panel mb-md"><div class="panel-header">Session Flow <span class="count">${steps.length} steps</span></div>
      <div class="panel-body" style="padding:12px;overflow-x:auto">
      <svg width="${svgW}" height="70" style="width:100%;max-width:${svgW}px;height:auto">
      <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="var(--accent)"/></marker></defs>`;
    const stepsY=18;
    steps.forEach((st,i)=>{
      const x=i*(bw+bg);const cs=['#26c68a','#00bcd4','#c792ea','#ffc857','#ff5370','#82aaff','#f78c6c','#89ddff'][i%8];
      html+=`<rect x="${x}" y="${stepsY}" width="${bw}" height="${bh}" rx="5" fill="rgba(0,0,0,0.2)" stroke="${cs}" stroke-width="1.5"/>`;
      html+=`<text x="${x+bw/2}" y="${stepsY+bh/2+4}" text-anchor="middle" fill="${cs}" font-size="9" font-weight="500">${st.slice(0,20)}</text>`;
      if(i<steps.length-1)html+=`<line x1="${x+bw}" y1="${stepsY+bh/2}" x2="${x+bw+bg}" y2="${stepsY+bh/2}" stroke="var(--accent)" stroke-width="1.5" marker-end="url(#a)"/>`;
    });
    html+=`</svg></div></div>`;
    // Summary
    if(sum){['sop_workflows','context_to_remember','effective_operations','pitfalls_and_fixes','wasted_actions','bottlenecks','efficiency_tip'].forEach(k=>{
      if(sum[k])html+=`<div class="panel mb-sm"><div class="panel-header">${k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</div><div class="panel-body" style="padding:10px 16px"><div class="text-sm" style="color:var(--text-secondary);line-height:1.7">${escHtml(sum[k])}</div></div></div>`;
    });}
    // Tools used
    html+=`<div class="panel mb-sm"><div class="panel-header">Tools Used</div><div class="panel-body" style="padding:8px 16px"><div class="flex gap-sm" style="flex-wrap:wrap">`;
    Object.entries(toolCnt).sort((a,b)=>b[1]-a[1]).forEach(([tool,cnt])=>{
      const mc={Skill:'red',Bash:'green',Read:'blue',Write:'yellow',Edit:'purple',Glob:'cyan',Grep:'accent'};
      const cc=mc[tool]||'accent';
      html+=`<span class="tag tag-tool" style="border-color:var(--${cc}-border);background:var(--${cc}-bg);color:var(--${cc})">${tool} (${cnt})</span>`;
    });
    html+=`</div></div></div>`;
    // Timeline inline
    html+=`<div class="panel"><div class="panel-header">Timeline <span class="count">${time.length} events</span></div>
      <div class="panel-body" style="max-height:400px;overflow-y:auto;padding:0">`;
    if(time.length>0)time.slice(0,80).forEach(e=>{
      const ic={message:{user:'💬',assistant:'🤖'},tool_call:{Task:'🔧',Bash:'💻',Read:'📖',Write:'✏️',Edit:'🖊',Skill:'⚡',Glob:'🔍',default:'🔧'},file_op:{read:'📖',write:'✏️',edit:'🖊',delete:'🗑',default:'📄'}};
      let icon='•',cls='';
      if(e.kind==='message'){icon=ic.message[e.subtype]||'💬';cls=e.subtype==='user'?'tag-skill':'tag-tool';}
      else if(e.kind==='tool_call'){icon=ic.tool_call[e.tool]||ic.tool_call.default;cls='tag-tool';}
      else if(e.kind==='file_op'){icon=ic.file_op[e.subtype]||ic.file_op.default;cls='tag-file';}
      html+=`<div class="timeline-item" style="padding:4px 10px"><div class="timeline-icon" style="font-size:11px">${icon}</div><div><span class="tag ${cls}">${e.tool||e.subtype||e.kind}</span></div><div class="timeline-content"><span class="text-xs text-muted">${escHtml(trunc(e.detail||'',100))}</span></div><div class="timeline-time text-xs text-muted">${e.ts?e.ts.slice(11,19):''}</div></div>`;
    });
    else html+='<div class="empty-state" style="padding:20px">No timeline</div>';
    html+=`</div></div>`;
    c.innerHTML=html;
  }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
}

// OVERVIEW
async function loadOverview(){
  const d=await fetchJSON(API+'/overview'),{total_sessions:t,total_messages:m,total_tools:tl,total_skills:s,total_knowledge:k,active_sessions:a,tool_distribution:td,daily_sessions:ds,recent_sessions:rs}=d;
  const mD=Math.max(...ds.map(x=>x.c),1),mT=Math.max(...td.map(x=>x.c),1);
  $('#main').innerHTML='<div class="content"><div class="flex flex-between" style="align-items:baseline"><div><div class="page-title">Analytics Overview</div><div class="page-subtitle">Real-time session monitoring</div></div><div class="text-xs text-muted" style="text-align:right">auto-refresh 15s</div></div>'
  +'<div class="stat-grid">'
  +'<div class="stat-card" onclick="navigate(\'sessions\')"><div class="label">Sessions</div><div class="value blue">'+t+'</div><div class="sub">'+a+' active</div></div>'
  +'<div class="stat-card"><div class="label">Messages</div><div class="value cyan">'+fmtNum(m)+'</div></div>'
  +'<div class="stat-card" onclick="navigate(\'tools\')"><div class="label">Tool Calls</div><div class="value green">'+fmtNum(tl)+'</div></div>'
  +'<div class="stat-card" onclick="navigate(\'skills\')"><div class="label">Skills</div><div class="value red">'+s+'</div></div>'
  +'<div class="stat-card" onclick="navigate(\'knowledge\')"><div class="label">Knowledge</div><div class="value purple">'+k+'</div></div></div>'
  +'<div class="grid-2 mb-lg"><div class="panel"><div class="panel-header">Daily Sessions <span class="count" id="drl">last 14d</span></div>'
  +'<div class="flex gap-sm" style="padding:4px 18px">'+[7,14,30,90,180,365].map(n=>'<span class="range-btn'+(n===14?' active':'')+'" onclick="loadDR('+n+')">'+n+'d</span>').join('')+'</div>'
  +'<div class="chart-bar-group" id="dchart">'+ds.slice().reverse().map(x=>'<div class="chart-bar" style="height:'+Math.max((x.c/mD)*75,5)+'px"><span class="tip">'+x.day.slice(5)+': '+x.c+'</span></div>').join('')+'</div>'
  +'<div class="chart-labels">'+ds.slice().reverse().map(x=>'<span>'+x.day.slice(5)+'</span>').join('')+'</div></div>'
  +'<div class="panel"><div class="panel-header">Tools <span class="count">top 10</span></div><div class="panel-body" style="padding:10px 18px">'
  +td.map(x=>{const p=(x.c/mT)*100;return '<div class="flex flex-between mb-sm" onclick="navigate(\'tools\')" style="cursor:pointer"><span class="tag tag-tool">'+x.tool+'</span><div style="flex:1;margin:0 10px"><div class="bar"><div class="bar-fill accent" style="width:'+p+'%"></div></div></div><span class="text-sm text-muted">'+x.c+'</span></div>';}).join('')
  +'<div class="text-xs text-muted" style="text-align:center;margin-top:8px;cursor:pointer" onclick="navigate(\'tools\')">View all tools →</div></div></div></div>'
  +'<div class="panel"><div class="panel-header">Recent Sessions <span class="count">latest 10</span></div><div class="panel-body"><table><tr><th>Session</th><th>IDE</th><th>Project</th><th>Initiative</th><th class="text-right">Msgs</th><th class="text-right">Tools</th><th>Started</th><th></th></tr>'
  +rs.map(x=>expRow('<td><span class="clickable" onclick="event.stopPropagation();viewSession(\''+x.id+'\')">'+shortId(x.id,22)+'</span></td><td>'+ideIconHtml(x.ide)+'</td><td>'+(x.project||'-')+'</td><td>'+(x.initiative?'<span class="tag tag-session">'+x.initiative+'</span>':'-')+'</td><td class="text-right">'+(x.message_count||0)+'</td><td class="text-right">'+(x.tool_count||0)+'</td><td class="text-sm text-muted">'+fmtTime(x.created_at)+'</td>','<div class="flex gap-lg"><div><span class="text-xs text-muted">Duration:</span> <span>'+(x.duration_min||'-')+'m</span></div><div><span class="text-xs text-muted">IDE:</span> '+ideIconHtml(x.ide)+'</div><div><span class="text-xs text-muted">Branch:</span> <span>'+(x.branch||'-')+'</span></div><div><span class="text-xs text-muted">Model:</span> <span>'+(x.model||'-')+'</span></div><div><span class="clickable text-sm" onclick="viewSession(\''+x.id+'\')">View Timeline →</span></div></div>')).join('')
  +'</table></div></div></div>';
}

async function loadDR(d){$$('.range-btn').forEach(b=>b.classList.toggle('active',b.textContent===d+'d'));document.getElementById('drl').textContent='last '+d+'d';
  try{const r=await fetchJSON(API+'/daily-sessions?days='+d),mD=Math.max(...r.map(x=>x.c),1);const el=document.getElementById('dchart');if(el)el.innerHTML=r.map(x=>'<div class="chart-bar" style="height:'+Math.max((x.c/mD)*75,5)+'px"><span class="tip">'+x.day.slice(5)+': '+x.c+'</span></div>').join('');}catch(e){}
}

// PROJECTS
async function loadProjects(){
  try {
    const d=await fetchJSON(API+'/projects');
    if(!d||d.length===0){$('#main').innerHTML='<div class="content"><div class="page-title">Projects</div><div class="panel"><div class="panel-body" style="padding:24px;text-align:center;color:var(--text-muted)">No projects data. Sessions need project attribution.</div></div></div>';return;}
    const mS=Math.max(...d.map(x=>x.session_count||0),1);
    $('#main').innerHTML='<div class="content"><div class="page-title">Projects</div><div class="page-subtitle">Cross-project metrics comparison</div>'
    +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Projects</div><div class="value blue">'+d.length+'</div></div><div class="stat-card"><div class="label">Sessions</div><div class="value">'+d.reduce((a,x)=>a+(x.session_count||0),0)+'</div></div><div class="stat-card"><div class="label">Tools</div><div class="value green">'+fmtNum(d.reduce((a,x)=>a+(x.total_tools||0),0))+'</div></div></div>'
    +'<div class="panel"><div class="panel-body"><table><tr><th>Project</th><th class="text-right">Sessions</th><th class="text-right">Messages</th><th class="text-right">Tool Calls</th><th class="text-right">Skills</th><th class="text-right">Avg Dur</th><th>Last Active</th></tr>'
    +d.map(x=>'<tr><td><span class="tag '+(x.project_name==='root'?'tag-skill':'tag-file')+'">'+(x.project_name||'unknown')+'</span></td><td class="text-right">'+fmtNum(x.session_count)+'</td><td class="text-right">'+fmtNum(x.total_messages)+'</td><td class="text-right">'+fmtNum(x.total_tools)+'</td><td class="text-right text-xs">'+(x.ides?Object.keys(x.ides).join(', '):'-')+'</td><td class="text-sm text-muted">'+(x.last_session||'').slice(0,16)+'</td></tr>').join('')
    +'</table></div></div></div>';
  } catch(e) { $('#main').innerHTML='<div class="content"><div class="page-title">Projects</div><div class="error">Failed to load: '+e.message+'</div></div>'; }
}

// SESSIONS
let sCache=[],sF={id:'',ide:'',project:'',initiative:''};
function pName(x){return x.project||(x.cwd?x.cwd.split('/').pop()||x.cwd:'-');}
function applySF(){document.querySelectorAll('.sess-filter').forEach(i=>sF[i.dataset.key]=i.value.toLowerCase());
  const f=sCache.filter(x=>(!sF.id||(x.id||'').toLowerCase().includes(sF.id))&&(!sF.ide||(x.ide||'').toLowerCase().includes(sF.ide))&&(!sF.project||(pName(x).toLowerCase().includes(sF.project))&&(!sF.initiative||(x.initiative||'').toLowerCase().includes(sF.initiative))));
  document.getElementById('sBody').innerHTML=f.map(x=>expRow('<td><span class="clickable text-monospace text-xs">'+shortId(x.id,22)+'</span></td><td>'+ideIconHtml(x.ide)+'</td><td>'+pName(x)+(x.project?'':' <span class="text-xs text-muted" style="font-size:9px">from cwd</span>')+'</td><td>'+(x.initiative?'<span class="tag tag-session">'+x.initiative+'</span>':'-')+'</td><td class="text-right">'+(x.message_count||0)+'</td><td class="text-right">'+(x.tool_count||0)+'</td><td class="text-right">'+(x.duration_min?x.duration_min+'m':'-')+'</td><td class="text-sm text-muted">'+fmtTime(x.created_at)+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading...</span></div>',x.id)).join('');}
async function loadSessions(){const d=await fetchJSON(API+'/sessions?limit=2000');sCache=d;renderS(d);}
function renderS(d){const tm=d.reduce((a,x)=>a+(x.message_count||0),0),tt=d.reduce((a,x)=>a+(x.tool_count||0),0);
  const allIde=[...new Set(d.map(x=>x.ide).filter(Boolean))].sort(),allProj=[...new Set(d.map(x=>x.project||(x.cwd?x.cwd.split('/').pop():'')).filter(Boolean))].sort(),allInit=[...new Set(d.map(x=>x.initiative).filter(Boolean))].sort();
  $('#main').innerHTML='<div class="content"><div class="page-title">Sessions</div><div class="page-subtitle">All recorded AI coding sessions</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Sessions</div><div class="value blue">'+d.length+'</div></div><div class="stat-card"><div class="label">Messages</div><div class="value cyan">'+fmtNum(tm)+'</div></div><div class="stat-card"><div class="label">Tools</div><div class="value green">'+fmtNum(tt)+'</div></div></div>'
  +'<div class="flex gap-md mb-md" style="flex-wrap:wrap">'
  +'<span class="search-box" style="flex:1;min-width:120px"><input class="sess-filter" list="sId" data-key="id" placeholder="Session ID..." oninput="applySF()"/></span>'
  +'<span class="search-box" style="flex:1;min-width:80px"><input class="sess-filter" list="sIde" data-key="ide" placeholder="IDE..." oninput="applySF()"/><datalist id="sIde">'+allIde.map(x=>'<option value="'+x+'">').join('')+'</datalist></span>'
  +'<span class="search-box" style="flex:1;min-width:120px"><input class="sess-filter" list="sProj" data-key="project" placeholder="Project..." oninput="applySF()"/><datalist id="sProj">'+allProj.map(x=>'<option value="'+x+'">').join('')+'</datalist></span>'
  +'<span class="search-box" style="flex:1;min-width:120px"><input class="sess-filter" list="sInit" data-key="initiative" placeholder="Initiative..." oninput="applySF()"/><datalist id="sInit">'+allInit.map(x=>'<option value="'+x+'">').join('')+'</datalist></span>'
  +'</div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>ID</th><th>IDE</th><th>Project</th><th>Initiative</th><th class="text-right">Msgs</th><th class="text-right">Tools</th><th class="text-right">Dur</th><th>Started</th><th></th></tr><tbody id="sBody">'
  +d.map(x=>expRow('<td><span class="clickable text-monospace text-xs" onclick="event.stopPropagation();viewSession(\''+x.id+'\')">'+shortId(x.id,22)+'</span></td><td>'+ideIconHtml(x.ide)+'</td><td>'+pName(x)+(x.project?'':' <span class="text-xs text-muted" style="font-size:9px">via cwd</span>')+'</td><td>'+(x.initiative?'<span class="tag tag-session">'+x.initiative+'</span>':'-')+'</td><td class="text-right">'+(x.message_count||0)+'</td><td class="text-right">'+(x.tool_count||0)+'</td><td class="text-right">'+(x.duration_min?x.duration_min+'m':'-')+'</td><td class="text-sm text-muted">'+fmtTime(x.created_at)+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading...</span></div>',x.id)).join('')
  +'</tbody></table></div></div></div>';
}

// MODELS
async function loadModels(){const d=await fetchJSON(API+'/models');
  const tc=d.reduce((a,x)=>a+(x.total_cost||0),0),tt=d.reduce((a,x)=>a+(x.total_tokens_in||0)+(x.total_tokens_out||0)+(x.total_tokens_reasoning||0)+(x.total_tokens_cache_read||0)+(x.total_tokens_cache_write||0),0);
  $('#main').innerHTML='<div class="content"><div class="page-title">Models</div><div class="page-subtitle">Token consumption, cost, and performance by model</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Models</div><div class="value cyan">'+d.length+'</div></div><div class="stat-card"><div class="label">Total Tokens</div><div class="value blue">'+fmtNum(tt)+'</div></div><div class="stat-card"><div class="label">Total Cost</div><div class="value green">$'+tc.toFixed(4)+'</div></div></div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>Model</th><th class="text-right">Sess</th><th class="text-right">TokIn</th><th class="text-right">TokOut</th><th class="text-right">CacheR</th><th class="text-right">Reason</th><th class="text-right">Cost</th><th></th></tr>'
  +d.map(x=>expRow('<td><span class="tag tag-tool">'+x.model_group+'</span></td><td class="text-right">'+x.session_count+'</td><td class="text-right">'+fmtNum(x.total_tokens_in||0)+'</td><td class="text-right">'+fmtNum(x.total_tokens_out||0)+'</td><td class="text-right">'+fmtNum(x.total_tokens_cache_read||0)+'</td><td class="text-right">'+fmtNum(x.total_tokens_reasoning||0)+'</td><td class="text-right">$'+(x.total_cost||0).toFixed(4)+'</td>',
    '<div class="flex gap-lg flex-wrap"><div><span class="text-xs text-muted">Sessions:</span> <span>'+x.session_count+'</span></div><div><span class="text-xs text-muted">Requests:</span> <span>'+(x.request_count||0)+'</span></div><div><span class="text-xs text-muted">Tokens In:</span> <span>'+fmtNum(x.total_tokens_in||0)+'</span></div><div><span class="text-xs text-muted">Tokens Out:</span> <span>'+fmtNum(x.total_tokens_out||0)+'</span></div><div><span class="text-xs text-muted">Cache Read:</span> <span>'+fmtNum(x.total_tokens_cache_read||0)+'</span></div><div><span class="text-xs text-muted">Reasoning:</span> <span>'+fmtNum(x.total_tokens_reasoning||0)+'</span></div><div><span class="text-xs text-muted">Cache Write:</span> <span>'+fmtNum(x.total_tokens_cache_write||0)+'</span></div><div><span class="text-xs text-muted">Total:</span> <span style="color:var(--accent);font-weight:600">'+fmtNum((x.total_tokens_in||0)+(x.total_tokens_out||0)+(x.total_tokens_reasoning||0)+(x.total_tokens_cache_read||0)+(x.total_tokens_cache_write||0))+'</span></div><div><span class="text-xs text-muted">Avg duration:</span> <span>'+Math.round(x.avg_duration_ms||0)+'ms</span></div><div><span class="text-xs text-muted">Max duration:</span> <span>'+Math.round(x.max_duration_ms||0)+'ms</span></div></div>')).join('')
  +'</table></div></div></div>';
}

// SKILLS
async function loadSkills(){const d=await fetchJSON(API+'/skills');const mC=Math.max(...d.map(x=>x.total_calls),1),tC=d.reduce((a,x)=>a+x.total_calls,0);
  // Build session count per skill from skill-detail and mentions
  let sessCnt={},mentCnt={};try{const dd=await fetchJSON(API+'/skill-detail?days=3650');for(const x of dd){if(!sessCnt[x.skill_name])sessCnt[x.skill_name]=new Set();sessCnt[x.skill_name].add(x.session_id);}}catch(e){}
  // Fetch session IDs for legacy skills not in tool_calls
  try{await Promise.all(d.filter(s=>!sessCnt[s.name]&&s.total_calls>0).map(async s=>{try{const[ids,mids]=await Promise.all([fetchJSON(API+'/skill-session-ids?name='+encodeURIComponent(s.name)),fetchJSON(API+'/skill-mentions?name='+encodeURIComponent(s.name)).catch(()=>[])]);sessCnt[s.name]=new Set(ids);mentCnt[s.name]=new Set([...ids,...mids]);}catch(e){}}));}catch(e){}
  const sessCounts={};Object.entries(sessCnt).forEach(([k,v])=>{sessCounts[k]=v.size;});
  const mentCounts={};Object.entries(mentCnt).forEach(([k,v])=>{mentCounts[k]=v.size;});
  $('#main').innerHTML='<div class="content"><div class="page-title">Skills</div><div class="page-subtitle">Skill usage, invocation patterns</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Skills</div><div class="value red">'+d.length+'</div></div><div class="stat-card"><div class="label">Calls</div><div class="value">'+tC+'</div></div><div class="stat-card"><div class="label">Avg/Skill</div><div class="value cyan">'+(tC/Math.max(d.length,1)).toFixed(1)+'</div></div></div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>Skill</th><th class="text-right">Calls</th><th class="text-right">Sess</th><th class="text-right">Ment</th><th>Usage</th><th class="text-right">%</th><th></th></tr>'
  +d.map(x=>{const sc=sessCounts[x.name]||0;const mc=mentCounts[x.name]||0;const hasSess=sc>0;const hasMent=mc>0&&!hasSess;return expRow('<td><span class="tag tag-skill">'+x.name+'</span>'+((hasSess?' <span class="tag tag-file" style="font-size:8px">'+sc+' sess</span>':'')||(hasMent?' <span class="tag tag-knowledge" style="font-size:8px">mentioned</span>':''))+'</td><td class="text-right">'+x.total_calls+'</td><td class="text-right"><span style="color:'+(hasSess?'var(--green)':'var(--text-secondary)')+'">'+(sc||'—')+'</span></td><td class="text-right"><span style="color:'+(hasMent?'var(--yellow)':'var(--text-secondary)')+'">'+(mc||'—')+'</span></td><td><div class="bar" style="width:80px"><div class="bar-fill red" style="width:'+(x.total_calls/mC*100)+'%"></div></div></td><td class="text-right">'+(x.total_calls/tC*100).toFixed(1)+'%</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading sessions...</span></div>','skill:'+x.name);}).join('')
  +'</table></div></div></div>';
}

// TOOLS
async function loadTools(){const d=await fetchJSON(API+'/tools');const mC=Math.max(...d.map(x=>x.calls),1),tC=d.reduce((a,x)=>a+x.calls,0);
  $('#main').innerHTML='<div class="content"><div class="page-title">Tools</div><div class="page-subtitle">All tool invocations</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Calls</div><div class="value blue">'+fmtNum(tC)+'</div></div><div class="stat-card"><div class="label">Unique</div><div class="value cyan">'+d.length+'</div></div><div class="stat-card"><div class="label">Avg Duration</div><div class="value green">'+Math.round(d.reduce((a,x)=>a+(x.avg_ms||0),0)/Math.max(d.length,1))+'ms</div></div></div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>Tool</th><th>Type</th><th class="text-right">Calls</th><th>Usage</th><th class="text-right">Avg ms</th><th class="text-right">Max ms</th><th></th></tr>'
  +d.map(x=>expRow('<td><span class="tag tag-tool">'+x.tool+'</span></td><td>'+(x.tool_type||'builtin')+(x.server_name?' <span class="tag tag-mcp">'+x.server_name+'</span>':'')+'</td><td class="text-right">'+x.calls+'</td><td><div class="bar" style="width:120px"><div class="bar-fill blue" style="width:'+(x.calls/mC*100)+'%"></div></div></td><td class="text-right">'+(x.avg_ms||'-')+'</td><td class="text-right text-muted">'+(x.max_ms||'-')+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading sessions...</span></div>','tool:'+x.tool)).join('')
  +'</table></div></div></div>';
}

// FILES
// ── Files Page ──
let allFileCache = [];
async function loadFiles() {
  allFileCache = await fetchJSON(API + '/file-detail?limit=500');
  renderFileView(allFileCache);
}
function renderFileView(data) {
  const fm = {}, names = new Set(), dirs = new Set();
  data.forEach(x => {
    const fp = x.file_path || x.path || '';
    const sep = fp.lastIndexOf('/');
    names.add(sep >= 0 ? fp.slice(sep + 1) : fp);
    dirs.add(sep >= 0 ? fp.slice(0, sep) : '/');
    if (!fm[fp]) fm[fp] = { path: fp, reads: 0, writes: 0, projs: new Set(), inits: new Set(), brs: new Set(), lastTs: '', types: new Set() };
    const f = fm[fp]; if(x.op==='read')f.reads++; else f.writes++;
    if (x.project) f.projs.add(x.project); if (x.initiative) f.inits.add(x.initiative);
    if (x.branch) f.brs.add(x.branch); if (x.file_type) f.types.add(x.file_type);
    if (x.ts && x.ts > f.lastTs) f.lastTs = x.ts;
  });
  const files = Object.values(fm).sort((a, b) => (b.reads + b.writes) - (a.reads + a.writes));
  const allProjs = [...new Set(data.map(x => x.project).filter(Boolean))].sort();
  const allTypes = [...new Set(data.map(x => x.file_type).filter(Boolean))].sort();
  $('#main').innerHTML = '<div class="content"><div class="page-title">Files</div><div class="page-subtitle">Files read/written — click for history</div>'
    + '<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Files</div><div class="value green">' + files.length + '</div></div>'
    + '<div class="stat-card"><div class="label">Reads</div><div class="value blue">' + files.reduce((a, f) => a + f.reads, 0) + '</div></div>'
    + '<div class="stat-card"><div class="label">Writes</div><div class="value yellow">' + files.reduce((a, f) => a + f.writes, 0) + '</div></div></div>'
    + '<div class="flex gap-md mb-md" style="flex-wrap:wrap">'
    + '<span class="search-box" style="flex:1;min-width:120px"><input list="flNames" id="fFn" placeholder="File name..." oninput="applyFF()" /><datalist id="flNames">'+[...names].map(n=>'<option value="'+n+'">').join('')+'</datalist></span>'
    + '<span class="search-box" style="flex:1;min-width:120px"><input list="flDirs" id="fFd" placeholder="Folder..." oninput="applyFF()" /><datalist id="flDirs">'+[...dirs].map(d=>'<option value="'+d+'">').join('')+'</datalist></span>'
    + '<span class="search-box" style="flex:1;min-width:120px"><input list="flProjs" id="fPj" placeholder="Project..." oninput="applyFF()" /><datalist id="flProjs">'+allProjs.map(p=>'<option value="'+p+'">').join('')+'</datalist></span>'
    + '<span class="search-box" style="flex:1;min-width:90px"><input list="flTypes" id="fTy" placeholder="Type..." oninput="applyFF()" /><datalist id="flTypes">'+allTypes.map(t=>'<option value="'+t+'">').join('')+'</datalist></span>'
    + '</div><div class="panel"><div class="panel-body" style="padding:0;overflow-x:auto"><table id="fTbl" style="width:100%;table-layout:fixed">'
    + '<thead><tr><th style="width:22%;cursor:col-resize" onmousedown="cRes(event,0)">Name</th><th style="width:18%;cursor:col-resize" onmousedown="cRes(event,1)">Folder</th>'
    + '<th style="width:6%;cursor:col-resize" onmousedown="cRes(event,2)" class="text-right">Reads</th><th style="width:6%;cursor:col-resize" onmousedown="cRes(event,3)" class="text-right">Writes</th>'
    + '<th style="width:14%;cursor:col-resize" onmousedown="cRes(event,4)">Project</th><th style="width:14%;cursor:col-resize" onmousedown="cRes(event,5)">Initiative</th>'
    + '<th style="width:12%;cursor:col-resize" onmousedown="cRes(event,6)">Branch</th><th style="width:5%;cursor:col-resize" onmousedown="cRes(event,7)">Last</th><th style="width:3%"></th></tr></thead>'
    + '<tbody>' + files.map((f, i) => renderFRow(f, i)).join('') + '</tbody></table></div></div></div>';
}
function renderFRow(f, i) {
  const s = f.path.lastIndexOf('/'); const n = s >= 0 ? f.path.slice(s + 1) : f.path; const d = s >= 0 ? f.path.slice(0, s) : '/';
  const id = 'fx' + i;
  return '<tr class="exp-row" onclick="togFE(\'' + id + '\',\'' + escId(f.path) + '\')" style="cursor:pointer">'
    + '<td class="text-monospace text-xs" title="' + escHtml(f.path) + '">' + trunc(n, 35) + '</td>'
    + '<td class="text-xs text-muted">' + trunc(d, 30) + '</td>'
    + '<td class="text-right">' + f.reads + '</td><td class="text-right">' + f.writes + '</td>'
    + '<td class="text-xs">' + ([...f.projs].slice(0, 2).join(', ') || '-') + '</td><td class="text-xs">' + ([...f.inits].slice(0, 2).join(', ') || '-') + '</td>'
    + '<td class="text-xs text-muted">' + ([...f.brs].slice(0, 2).join(', ') || '-') + '</td><td class="text-xs text-muted">' + (f.lastTs ? fmtTime(f.lastTs) : '-') + '</td>'
    + '<td style="text-align:center">▶</td></tr>'
    + '<tr id="' + id + '" style="display:none"><td colspan="9" style="padding:0"><div id="' + id + '-c" style="padding:10px 14px;background:var(--bg-tertiary)"><div class="loading" style="padding:10px"><div class="spinner"></div></div></div></td></tr>';
}
function togFE(id, path) {
  const r = document.getElementById(id); if (!r) return;
  const s = r.style.display === 'none'; r.style.display = s ? 'table-row' : 'none';
  const ic = r.previousElementSibling?.querySelector('td:last-child');
  if (ic) ic.textContent = s ? '▼' : '▶';
  if (s) loadFE(id, path);
}
async function loadFE(id, path) {
  const c = document.getElementById(id + '-c'); if (!c || c.dataset.loaded) return; c.dataset.loaded = '1';
  try {
    const data = await fetchJSON(API + '/file-detail?file_path=' + encodeURIComponent(path) + '&limit=100');
    if (!data.length) { c.innerHTML = '<div class="text-xs text-muted" style="padding:8px">No ops</div>'; return; }
    c.innerHTML = '<div class="text-xs text-muted mb-sm">' + data.length + ' ops</div>'
      + data.slice(0, 50).map(x => '<div class="flex gap-md" style="padding:3px 0;font-size:11px;border-bottom:1px solid rgba(30,34,48,0.3)">'
        + '<span>' + (x.op === 'read' ? '📖' : '✏️') + '</span><span class="tag ' + (x.op === 'read' ? 'tag-file' : 'tag-tool') + '">' + x.op + '</span>'
        + '<span class="text-xs text-muted">' + (x.project || '-') + '</span>'
        + '<span class="text-xs text-muted">' + (x.initiative || '') + '</span>'
        + '<span class="text-xs text-muted">' + (x.skill_name ? 'via ' + x.skill_name : '') + '</span>'
        + '<span class="text-xs text-muted" style="margin-left:auto">' + fmtTime(x.ts) + '</span></div>').join('');
  } catch (e) { c.innerHTML = '<div class="text-xs text-muted" style="padding:8px">Error</div>'; }
}
function applyFF() {
  const nq = (document.getElementById('fFn')?.value || '').toLowerCase();
  const dq = (document.getElementById('fFd')?.value || '').toLowerCase();
  const pq = document.getElementById('fPj')?.value || '';
  const tq = document.getElementById('fTy')?.value || '';
  document.querySelectorAll('#fTbl tbody tr.exp-row').forEach(r => {
    const show = (!nq || (r.cells[0]?.textContent || '').toLowerCase().includes(nq))
      && (!dq || (r.cells[1]?.textContent || '').toLowerCase().includes(dq))
      && (!pq || (r.cells[4]?.textContent || '').includes(pq))
      && (!tq || (r.cells[0]?.textContent || '').toLowerCase().includes('.' + tq));
    r.style.display = show ? '' : 'none';
    const er = r.nextElementSibling; if (er && er.id) er.style.display = 'none';
  });
}
let crI = null, crX = 0;
function cRes(e, i) { crI = i; crX = e.clientX; document.addEventListener('mousemove', cMov); document.addEventListener('mouseup', cUp); e.preventDefault(); }
function cMov(e) { const ths = document.querySelectorAll('#fTbl th'); if (!ths[crI]) return; const cw = parseFloat(ths[crI].style.width) || 80; ths[crI].style.width = Math.max(30, cw + (e.clientX - crX) * 0.4) + 'px'; crX = e.clientX; }
function cUp() { document.removeEventListener('mousemove', cMov); document.removeEventListener('mouseup', cUp); }

// KNOWLEDGE
async function loadKnowledge(){const d=await fetchJSON(API+'/knowledge');const tc={trap:'red',best:'green',pattern:'blue',insight:'purple'};
  const totalValidations=d.reduce((a,x)=>a+(x.session_count||0),0);
  $('#main').innerHTML='<div class="content"><div class="page-title">Knowledge</div><div class="page-subtitle">Cross-session validated insights</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Insights</div><div class="value purple">'+d.length+'</div></div><div class="stat-card"><div class="label">Validations</div><div class="value green">'+totalValidations+'</div><div class="sub">across sessions</div></div></div>'
  +(d.length===0?'<div class="panel"><div class="empty-state"><div class="icon">📝</div>No knowledge cards</div></div>':
  '<div class="panel"><div class="panel-body"><table><tr><th>Type</th><th>Insight</th><th class="text-right">Validated by</th><th>First seen</th><th></th></tr>'
  +d.map(x=>expRow('<td><span class="tag tag-knowledge">'+(x.type||'unknown')+'</span></td><td><span class="text-sm" style="font-weight:500">'+escHtml(x.title||'Untitled')+'</span></td><td class="text-right"><span class="tag '+(x.session_count>1?'tag-file':'tag-tool')+'" style="font-size:10px">'+x.session_count+' sessions</span></td><td class="text-sm text-muted">'+((x.generated_at||'').slice(0,10))+'</td>',
  '<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading sessions...</span></div>','knowledge:'+x.id)).join('')
  +'</table></div></div></div>');
}

// Handle knowledge expand
async function _loadKnowledgeSessions(id, kid){
  const c=document.getElementById(id+'-c');if(!c||c.dataset.loaded)return;c.dataset.loaded='1';
  c.innerHTML='<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading...</span></div>';
  try{
    const [kSess,sessions,allK]=await Promise.all([
      fetchJSON(API+'/knowledge/'+kid+'/sessions'),
      fetchJSON(API+'/sessions?limit=500'),
      fetchJSON(API+'/knowledge')
    ]);
    // Find this knowledge card
    const card=allK.find(k=>k.id==kid);
    const sids=new Set(kSess.map(s=>s.session_id));
    const filtered=sessions.filter(s=>sids.has(s.id));
    let html='';
    // Detail sections
    if(card){
      const sections=[
        {label:'🎯 What I Was Working On',key:'summary'},
        {label:'✅ Lessons & Experience',key:'evidence'},
        {label:'🚫 What To Avoid',key:'pitfalls_and_fixes'},
        {label:'⚠️ Problems & Retries',key:'wasted_actions'},
      ];
      html+='<div class="summary-grid mb-md">';
      sections.forEach(sec=>{
        const val=card[sec.key];
        if(val&&val.length>5){
          html+=`<div class="summary-card"><div class="label">${sec.label}</div><div class="text">${trunc(escHtml(val),300)}</div></div>`;
        }
      });
      html+='</div>';
    }
    // Validated by sessions
    html+='<div class="panel"><div class="panel-header">Validated by <span class="count">'+kSess.length+' sessions</span></div><div class="panel-body" style="padding:0">';
    if(filtered.length>0){
      html+='<table style="width:100%"><tr><th>Session</th><th>IDE</th><th>Project</th><th>Initiative</th><th>Started</th></tr>';
      filtered.forEach(s=>{
        html+=`<tr style="cursor:pointer" onclick="viewSession('${s.id}')"><td class="text-monospace text-xs">${shortId(s.id,20)}</td><td>${ideIconHtml(s.ide)}</td><td class="text-xs">${s.project||'-'}</td><td>${s.initiative?`<span class="tag tag-session" style="font-size:9px">${s.initiative}</span>`:'-'}</td><td class="text-xs text-muted">${fmtTime(s.created_at)}</td></tr>`;
      });
      html+='</table>';
    }else{
      kSess.forEach(s=>{
        html+=`<div class="timeline-item" style="padding:4px 14px"><div class="timeline-icon">✓</div><div class="timeline-content"><span class="text-xs text-muted">${s.session_id||''}</span></div><div class="timeline-time text-xs text-muted">${(s.validated_at||'').slice(0,10)}</div></div>`;
      });
    }
    html+='</div></div>';
    c.innerHTML=html;
  }catch(e){c.innerHTML='<div class="text-sm text-muted" style="padding:12px">Error: '+e.message+'</div>';}
}

// INITIATIVES
async function loadInitiatives(){const d=await fetchJSON(API+'/initiatives');
  $('#main').innerHTML='<div class="content"><div class="page-title">Initiatives</div><div class="page-subtitle">Cross-session workstreams</div>'
  +(d.length===0?'<div class="panel"><div class="empty-state"><div class="icon">📋</div>No initiatives</div></div>':
  '<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Initiatives</div><div class="value yellow">'+d.length+'</div></div><div class="stat-card"><div class="label">Sessions</div><div class="value blue">'+d.reduce((a,x)=>a+x.session_count,0)+'</div></div><div class="stat-card"><div class="label">Tools</div><div class="value green">'+fmtNum(d.reduce((a,x)=>a+x.tool_count,0))+'</div></div></div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>Initiative</th><th>Project</th><th class="text-right">Sessions</th><th class="text-right">Tools</th><th></th></tr>'
  +d.map(x=>expRow('<td><span class="tag tag-session">'+x.initiative+'</span></td><td>'+(x.project||'-')+'</td><td class="text-right">'+x.session_count+'</td><td class="text-right">'+x.tool_count+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading sessions...</span></div>','initiative:'+x.initiative)).join('')
  +'</table></div></div>')+'</div>';
}

// SESSION DETAIL
async function viewSession(id){const[det,time]=await Promise.all([fetchJSON(API+'/sessions/'+id),fetchJSON(API+'/sessions/'+id+'/timeline').catch(()=>[])]);const s=det.session,sum=det.summary,st=det.stats||{};
  const msgCount=st.message_count??det.messages.length,toolCount=st.tool_count??det.tool_calls.length,fileCount=st.read_count!=null?(st.read_count||0)+(st.write_count||0):det.file_ops.length;
  let dur=st.duration_min;if(!dur&&s?.created_at&&s?.closed_at)dur=Math.max(1,Math.round((new Date(s.closed_at)-new Date(s.created_at))/60000));
  $('#main').innerHTML='<div class="content"><div class="flex flex-between mb-lg"><div><div class="page-title">Session Detail</div><div class="page-subtitle">'+ideIconHtml(s.ide)+''+(s.project?' <span class="tag tag-file">'+s.project+'</span>':'')+(s.initiative?' <span class="tag tag-session">'+s.initiative+'</span>':'')+' <span class="text-muted" style="margin-left:8px;font-size:11px">'+shortId(s.id,30)+'</span></div></div><span class="clickable" onclick="goBack()">← Back</span></div>'
  +'<div class="stat-grid" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr))"><div class="stat-card"><div class="label">Messages</div><div class="value" style="font-size:22px">'+fmtNum(msgCount)+'</div></div><div class="stat-card"><div class="label">Tools</div><div class="value blue" style="font-size:22px">'+fmtNum(toolCount)+'</div></div><div class="stat-card"><div class="label">Files</div><div class="value green" style="font-size:22px">'+fmtNum(fileCount)+'</div></div><div class="stat-card"><div class="label">Skills</div><div class="value red" style="font-size:22px">'+(st.skill_count||0)+'</div></div><div class="stat-card"><div class="label">Bash</div><div class="value yellow" style="font-size:22px">'+(st.bash_count||0)+'</div></div><div class="stat-card"><div class="label">Duration</div><div class="value cyan" style="font-size:22px">'+(dur?dur+'m':'-')+'</div></div></div>'
  +'<div class="panel mb-lg"><div class="panel-header">Session Info</div><div class="panel-body" style="padding:12px 16px"><div class="grid-2"><div class="summary-card"><div class="label">Session ID</div><div class="text text-monospace text-xs">'+s.id+'</div></div><div class="summary-card"><div class="label">IDE</div><div class="text">'+(s.ide||'-')+'</div></div><div class="summary-card"><div class="label">Project</div><div class="text">'+(s.project||'(root)')+'</div></div><div class="summary-card"><div class="label">Initiative</div><div class="text">'+(s.initiative||'-')+'</div></div><div class="summary-card"><div class="label">Model</div><div class="text text-xs">'+fmtModel(s.model)+'</div></div><div class="summary-card"><div class="label">Branch</div><div class="text text-monospace text-xs">'+(s.branch||'-')+'</div></div><div class="summary-card"><div class="label">Working Dir</div><div class="text text-monospace text-xs">'+(s.cwd||'-')+'</div></div><div class="summary-card"><div class="label">Started</div><div class="text">'+fmtTime(s.created_at)+'</div></div><div class="summary-card"><div class="label">Ended</div><div class="text">'+(s.closed_at?fmtTime(s.closed_at):'(active)')+'</div></div>'+(st.cost?'<div class="summary-card"><div class="label">Cost</div><div class="text">$'+(+st.cost).toFixed(4)+'</div></div>':'')+'<div class="summary-card"><div class="label">Tokens</div><div class="text">'+(st?fmtNum((st.tokens_input||0)+(st.tokens_output||0)+(st.tokens_reasoning||0)+(st.tokens_cache_read||0)+(st.tokens_cache_write||0)):'0')+'</div></div></div></div>'
  +(sum?'<div class="panel mb-lg"><div class="panel-header">AI Summary</div><div class="panel-body" style="padding:14px"><div class="summary-grid"><div class="summary-card"><div class="label">Context</div><div class="text">'+(sum.context_to_remember||'-')+'</div></div><div class="summary-card"><div class="label">Efficiency Tip</div><div class="text">'+(sum.efficiency_tip||'-')+'</div></div><div class="summary-card"><div class="label">Keywords</div><div class="text">'+(sum.memory_keywords||'-')+'</div></div><div class="summary-card"><div class="label">Score</div><div class="text" style="font-size:18px;font-weight:700;color:'+((sum.efficiency_score||0)>.6?'var(--green)':'var(--yellow)')+'">'+(sum.efficiency_score?Math.round(sum.efficiency_score*100)+'%':'-')+'</div></div></div></div></div>':'')
  +'<div class="panel"><div class="panel-header">Timeline <span class="count">'+time.length+' events</span></div><div class="panel-body" style="max-height:600px;overflow-y:auto">'
  +(time.length===0?'<div class="empty-state"><div class="icon">📊</div>No timeline events recorded</div>':time.map(e=>{const ic={message:{u:'💬',a:'🤖'},tool_call:{Task:'🔧',Bash:'💻',Read:'📖',Write:'✏️',Edit:'🖊',Skill:'⚡',Grep:'🔎',default:'🔧'},file_op:{read:'📖',write:'✏️',edit:'🖊',delete:'🗑',default:'📄'}};let icon='•',cls='';if(e.kind==='message'){icon=ic.message[e.subtype]||'💬';cls=e.subtype==='user'?'tag-skill':'tag-tool';}else if(e.kind==='tool_call'){icon=ic.tool_call[e.tool]||ic.tool_call.default;cls='tag-tool';}else if(e.kind==='file_op'){icon=ic.file_op[e.subtype]||ic.file_op.default;cls='tag-file';}
  const dt=e.detail||'';const ti='te'+(''+Math.random()).slice(2,8);
return '<div class="flex flex-between" style="padding:6px 18px;border-bottom:1px solid rgba(30,34,48,0.3);cursor:pointer" onclick="toggleTl(\''+ti+'\')"><div class="flex gap-sm" style="flex:1;min-width:0"><span>'+icon+'</span><span class="tag '+cls+'">'+(e.tool||e.subtype||e.kind)+'</span><span class="text-sm text-muted" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" id="'+ti+'s">'+trunc(dt,120)+'</span><span class="text-sm text-muted" id="'+ti+'f" style="display:none;white-space:pre-wrap;word-break:break-word">'+escHtml(dt)+'</span></div><span class="text-xs text-muted">'+((e.ts||'').slice(11,19))+'</span></div>';}).join(''))
  +'</div></div></div>';
}


function toggleTl(id){
  const s=document.getElementById(id+'s'),f=document.getElementById(id+'f');
  if(!s||!f)return;const sh=f.style.display!=='block';
  s.style.display=sh?'none':'';
  f.style.display=sh?'block':'none';
}

// ── Tab Navigation ──
const TABS=[{id:'activity',label:'Activity',icon:'◉'},{id:'insights',label:'Insights',icon:'◎'},{id:'system',label:'System',icon:'⚙'}];
const SUBNAV={activity:[{id:'summary',label:'Summary',icon:'◉',load:loadOverview},{id:'sessions',label:'Sessions',icon:'☰',load:loadSessions},{id:'files',label:'Files',icon:'📁',load:loadFiles,toggle:1}],insights:[{id:'usage',label:'Usage',icon:'◫',load:loadProjects},{id:'cost',label:'Cost',icon:'💰',load:loadCost},{id:'quality',label:'Quality',icon:'🔍',load:loadQuality},{id:'knowledge',label:'Knowledge',icon:'✓',load:loadKnowledge}],system:[{id:'health',label:'Health',icon:'◉',load:loadHealth},{id:'errors',label:'Errors',icon:'⚠',load:loadErrors},{id:'evolution',label:'Evolution',icon:'⬡',load:loadEvolution}]};
const LOAD_MAP={};Object.values(SUBNAV).forEach(v=>v.forEach(i=>LOAD_MAP[i.id]=i.load));
let currentTab='activity';

function renderTopbar(){document.getElementById('topbar').innerHTML='<div class="topbar-tabs" id="topbar-tabs">'+TABS.map(t=>'<span class="tab'+(t.id==='activity'?' active':'')+'" data-tab="'+t.id+'" onclick="switchTab(\''+t.id+'\')">'+t.icon+' '+t.label+'</span>').join('')+'</div><div class="topbar-status"><span class="status-dot"></span><span class="status-text">Connected</span><span class="topbar-sdk">v2.0</span></div>';}
function switchTab(t){if(t===currentTab)return;currentTab=t;navigate(SUBNAV[t][0].id);}
function safeLoad(fn){return async function(){try{await fn();}catch(e){const c=document.querySelector('#main .content');if(c)c.innerHTML='<div class="panel-error"><div class="err-icon">⚠</div><div class="err-msg">'+escHtml(e.message)+'</div><button class="retry-btn" onclick="navigate(\''+currentView+'\')">↻ Retry</button></div>';}}}

async function loadHealth(){
  $('#main').innerHTML='<div class="content"><div class="page-title">◉ System Health</div><div class="page-subtitle">Model performance, tool latency, and system status</div>'+skStatCards(4)+'<div class="grid-2">'+skPanel('Model Performance',5)+skPanel('Tool Health',5)+'</div></div>';
  try{const[md,tl]=await Promise.all([fetchJSON(API+'/models').catch(()=>[]),fetchJSON(API+'/tools').catch(()=>[])]);const tc=md.reduce((a,x)=>a+(x.total_cost||0),0),tt=md.reduce((a,x)=>a+(x.total_tokens_in||0)+(x.total_tokens_out||0),0);const tlc=tl.reduce((a,x)=>a+(x.calls||0),0),al=tl.length?Math.round(tl.reduce((a,x)=>a+(x.avg_ms||0),0)/tl.length):0;
  $('#main').innerHTML='<div class="content"><div class="page-title">◉ System Health</div><div class="page-subtitle">Model performance, tool latency, and system status</div>'+'<div class="stat-grid"><div class="stat-card"><div class="label">Models</div><div class="value cyan">'+md.length+'</div><div class="sub">'+md.reduce((a,x)=>a+(x.session_count||0),0)+' sessions</div></div><div class="stat-card"><div class="label">Total Cost</div><div class="value green">$'+tc.toFixed(4)+'</div></div><div class="stat-card"><div class="label">Total Tokens</div><div class="value blue">'+fmtNum(tt)+'</div></div><div class="stat-card"><div class="label">Avg Latency</div><div class="value '+(al>5000?'yellow':'green')+'">'+al+'ms</div><div class="sub">'+tlc+' calls, '+tl.length+' tools</div></div></div><div class="grid-2"><div class="panel"><div class="panel-header">Model Performance<span class="count">'+md.length+' models</span></div><div class="panel-body"><table><tr><th>Model</th><th class="text-right">Sess</th><th class="text-right">In</th><th class="text-right">Out</th><th class="text-right">Cost</th></tr>'+md.map(m=>'<tr><td><span class="tag tag-tool">'+(m.model_group||'?')+'</span></td><td class="text-right">'+(m.session_count||0)+'</td><td class="text-right">'+fmtNum(m.total_tokens_in||0)+'</td><td class="text-right">'+fmtNum(m.total_tokens_out||0)+'</td><td class="text-right">$'+(m.total_cost||0).toFixed(4)+'</td></tr>').join('')+'</table></div></div><div class="panel"><div class="panel-header">Tool Health<span class="count">'+tl.length+' tools</span></div><div class="panel-body"><table><tr><th>Tool</th><th class="text-right">Calls</th><th class="text-right">Avg ms</th><th class="text-right">Max ms</th></tr>'+tl.map(t=>'<tr><td><span class="tag tag-tool">'+t.tool+'</span></td><td class="text-right">'+t.calls+'</td><td class="text-right">'+(t.avg_ms||'-')+'</td><td class="text-right">'+(t.max_ms||'-')+'</td></tr>').join('')+'</table></div></div></div></div>';}catch(e){const c=document.querySelector('#main .content');if(c)c.innerHTML='<div class="panel-error"><div class="err-icon">⚠</div><div class="err-msg">Failed: '+escHtml(e.message)+'</div><button class="retry-btn" onclick="loadHealth()">↻ Retry</button></div>';}
}

// ── Skeleton Helpers ──
function skStatCards(n){let h='<div class="sk-stat-grid">';for(let i=0;i<n;i++)h+='<div class="sk-card"><div class="sk-l"></div><div class="sk-v"></div><div class="sk-s"></div></div>';return h+'</div>';}
const skW=[65,45,80,55,70,35,90,60];
function skPanel(title,n){n=n||5;let h='<div class="sk-panel"><div class="sk-ph"><div class="sk" style="width:'+Math.min((title.length||8)*9,200)+'px"></div></div><div class="sk-pb">';for(let i=0;i<n;i++)h+='<div class="sk-r"><div class="sk" style="width:'+skW[i%skW.length]+'%"></div></div>';return h+'</div></div>';}
function skForView(v){switch(v){case'summary':return skStatCards(5)+'<div class="grid-2 mb-lg">'+skPanel('Daily Sessions',7)+skPanel('Tools',7)+'</div>'+skPanel('Recent Sessions',6);case'sessions':case'files':return skStatCards(3)+skPanel('Data',8);case'hotspots':return skPanel('File Hotspots',10);case'usage':return skStatCards(3)+skPanel('Usage',10);case'cost':return skStatCards(3)+skPanel('Cost Details',8);case'quality':return skStatCards(3)+skPanel('Quality Metrics',8);case'knowledge':return skStatCards(2)+skPanel('Knowledge',8);case'health':return skStatCards(4)+'<div class="grid-2">'+skPanel('Models',5)+skPanel('Tools',5)+'</div>';case'errors':return '<div class="grid-2">'+skPanel('Tool Errors',6)+skPanel('Error Sessions',6)+'</div>';case'evolution':return skStatCards(5)+'<div class="grid-2">'+skPanel('Skills',6)+skPanel('Experiences',6)+'</div>';default:return skStatCards(3)+skPanel('Data',5);}}

// ── Info Tooltip ──
function infoTrigger(title,source,purpose){return '<span class="info-trigger">ℹ<span class="info-tip"><span class="tip-title">'+escHtml(title)+'</span><span class="tip-source">'+escHtml(source)+'</span><span class="tip-purpose">'+escHtml(purpose)+'</span></span></span>';}
const INFO_MAP={summary:{'Sessions':{source:'overview.total_sessions',purpose:'Total AI coding sessions recorded'},'Messages':{source:'overview.total_messages',purpose:'Assistant + user messages across sessions'},'Tool Calls':{source:'overview.tool_distribution',purpose:'Aggregated tool invocation count'},'Skills':{source:'overview.total_skills',purpose:'Unique skills invoked'},'Knowledge':{source:'overview.total_knowledge',purpose:'Cross-session validated insights'}},'summary-th':{'Session':{source:'sessions.id',purpose:'Unique session identifier'},'IDE':{source:'sessions.ide',purpose:'CLI tool or editor used'}}};
function getInfo(v,l){const m=INFO_MAP[v];if(m&&m[l])return m[l];return{title:l,source:'api/'+v,purpose:'Metric from '+v+' view'};}
function enrichContent(){document.querySelectorAll('.stat-card .value').forEach(el=>{if(el.querySelector('.info-trigger'))return;const lb=(el.closest('.stat-card')?.querySelector('.label')?.textContent||'').trim();if(lb){const i=getInfo(currentView,lb);el.insertAdjacentHTML('beforeend',' '+infoTrigger(i.title,i.source,i.purpose));}});document.querySelectorAll('th').forEach(th=>{if(th.querySelector('.info-trigger'))return;const t=th.textContent.trim();if(t&&t.length<25&&!/^\d+$/.test(t)){const i=getInfo(currentView+'-th',t);th.insertAdjacentHTML('beforeend',' '+infoTrigger(i.title,i.source,i.purpose));}});}

// AUTO-REFRESH
let ri=null;
function startAR(view,ms){if(ri)clearInterval(ri);ri=setInterval(()=>{if(document.hidden)return;if(view==='summary')loadOverview();},ms);}
const _n=navigate;navigate=function(view,ph){if(ri)clearInterval(ri);_n(view,ph);if(view==='summary')startAR(view,15000);};

// ── Evolution (self-evolving-agent initiative) ──
async function loadEvolution(){try{const o=await fetchJSON(API+'/evolution/overview');const sk=await fetchJSON(API+'/evolution/skills?status=all');const ex=await fetchJSON(API+'/evolution/experiences?status=all');const sc=o.evolution_score>=50?'green':o.evolution_score>=30?'yellow':'red';$('#main').innerHTML='<div class="content"><div class="page-title">⬡ Evolution Monitor</div><div class="page-subtitle">Self-evolving agent metrics — skills, experiences, and pending review</div><div class="stat-grid"><div class="stat-card"><div class="label">Evolution Score</div><div class="value '+sc+'">'+o.evolution_score+'</div><div class="sub">/100 target ≥50</div></div><div class="stat-card"><div class="label">Auto-Trained Skills</div><div class="value green">'+o.auto_trained_skills+'</div></div><div class="stat-card"><div class="label">Experiences</div><div class="value blue">'+o.auto_trained_experiences+'</div></div><div class="stat-card"><div class="label">Skill Reuse Rate</div><div class="value">'+Math.round(o.skill_reuse_rate*100)+'%</div></div><div class="stat-card"><div class="label">Pending Review</div><div class="value '+(o.pending_review>0?'yellow':'green')+'">'+o.pending_review+'</div></div></div><div class="grid-2 mb-lg"><div class="panel"><div class="panel-header">Skills<span class="count">'+sk.length+'</span></div><div class="panel-body" style="max-height:400px;overflow-y:auto"><table><tr><th>Name</th><th>Source</th><th>Health</th><th>Calls</th><th>Sessions</th><th>Reuse</th></tr>'+(sk.length?sk.map(s=>'<tr><td><span class="clickable" onclick="viewEvolutionSkill(\''+escHtml(s.name)+'\')">'+escHtml(s.name)+'</span></td><td><span class="tag '+((s.provenance||'')==='agent'?'tag-ide-claude':(s.provenance||'')==='bundled'?'tag-ide-gemini':'tag-tool')+'">'+escHtml(s.provenance||'?')+'</span></td><td><span class="tag '+((s.state||'')==='active'?'tag-knowledge':(s.state||'')==='stale'?'tag-skill':'tag-tool')+'">'+escHtml(s.state||'?')+'</span></td><td>'+fmtNum(s.total_calls)+'</td><td>'+fmtNum(s.sessions_invoked)+'</td><td>'+Math.round(s.reuse_rate*100)+'%</td></tr>').join(''):'<tr><td colspan="6" class="text-muted">No skills</td></tr>')+'</table></div></div><div class="panel"><div class="panel-header">Experiences<span class="count">'+ex.length+'</span></div><div class="panel-body" style="max-height:400px;overflow-y:auto">'+(ex.length?ex.slice(0,50).map(e=>'<div style="padding:8px 12px;border-bottom:1px solid var(--border);font-size:11px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"><span class="tag tag-skill">'+escHtml(e.state||'active')+'</span><span class="tag tag-tool text-xs">'+escHtml(e.topic||'')+'</span></div><div style="color:var(--text-secondary);line-height:1.4">'+escHtml((e.memory||'').slice(0,200))+'</div><div style="margin-top:4px;display:flex;gap:8px;font-size:10px;color:var(--text-muted)"><span>📊 '+fmtNum(e.use_count)+' uses</span><span>📁 '+escHtml(e.project||'')+'</span>'+(e.last_used?'<span>🕐 '+e.last_used.slice(0,10)+'</span>':'')+'</div></div>').join(''):'<div style="padding:24px;text-align:center;color:var(--text-muted)">No experiences stored yet.</div>')+'</div></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="page-title">Evolution</div><div class="error">Failed: '+e.message+'. Ensure mem0 is configured (DEEPSEEK_API_KEY).</div></div>'}}
function renderMd(t){if(!t)return'';return t.split('\n').map(l=>{if(l.startsWith('# '))return'<h1 style=\"margin:16px 0 8px;font-size:18px\">'+escHtml(l.slice(2))+'</h1>';if(l.startsWith('## '))return'<h3 style=\"margin:14px 0 6px;font-size:14px;color:var(--text-primary)\">'+escHtml(l.slice(3))+'</h3>';if(l.startsWith('### '))return'<h4 style=\"margin:10px 0 4px;font-size:13px\">'+escHtml(l.slice(4))+'</h4>';if(l.match(/^\d+\.\s/))return'<li style=\"margin:2px 0 2px 16px\">'+escHtml(l.replace(/^\d+\.\s/,''))+'</li>';if(l.startsWith('- '))return'<li style=\"margin:2px 0 2px 16px\">'+escHtml(l.slice(2))+'</li>';if(l.startsWith('**')&&l.endsWith('**'))return'<p style=\"margin:4px 0;font-weight:600\">'+escHtml(l.slice(2,-2))+'</p>';if(l.trim()==='')return'<br>';return escHtml(l)+'<br>';}).join('')}
function viewEvolutionSkill(name){fetchJSON(API+'/evolution/skills/'+encodeURIComponent(name)).then(s=>{const desc=s.description||'';const content=s.content||'';const whenUse=s.when_to_use||'';const isPending=s.state==='pending';const sidList=(s.session_ids||[]).slice(0,10).map(id=>'<span class=\"tag tag-tool text-xs\">'+escHtml(id).slice(0,20)+'</span>').join(' ')||'none';const provCls=s.provenance==='agent'?'tag-ide-claude':s.provenance==='bundled'?'tag-ide-gemini':'tag-tool';const stateCls=s.state==='active'?'tag-knowledge':s.state==='stale'?'tag-skill':'tag-tool';const approveBtns=isPending?'<div class=\"flex gap-sm mt-md\" style=\"padding:12px 16px\"><button class=\"btn btn-primary\" onclick=\"approveSkill(\"'+escHtml(s.name)+'\")\"> Approve</button><button class=\"btn btn-warning\" onclick=\"rejectSkill(\"'+escHtml(s.name)+'\")\"> Reject</button></div>':'';$('#main').innerHTML='<div class=\"content\"><div class=\"page-title\" style=\"cursor:pointer\" onclick=\"navigate(\"evolution\")\">← ⬡ Skill: '+escHtml(s.name)+'</div><div class=\"stat-grid mb-lg\"><div class=\"stat-card\"><div class=\"label\">Source</div><div class=\"value\" style=\"font-size:14px\"><span class=\"tag '+provCls+'\">'+escHtml(s.provenance||'?')+'</span></div></div><div class=\"stat-card\"><div class=\"label\">Status</div><div class=\"value\" style=\"font-size:14px\"><span class=\"tag '+stateCls+'\">'+escHtml(s.state||'?')+'</span></div></div><div class=\"stat-card\"><div class=\"label\">Total Calls</div><div class=\"value blue\">'+fmtNum(s.total_calls)+'</div></div><div class=\"stat-card\"><div class=\"label\">Sessions</div><div class=\"value green\">'+fmtNum(s.sessions_invoked)+'</div></div><div class=\"stat-card\"><div class=\"label\">Reuse Rate</div><div class=\"value\">'+Math.round(s.reuse_rate*100)+'%</div></div></div>'+(desc?'<div class=\"panel mb-lg\"><div class=\"panel-header\">Description</div><div class=\"panel-body\" style=\"padding:16px;line-height:1.6;color:var(--text-secondary)\">'+escHtml(desc)+'</div></div>':'')+(whenUse?'<div class=\"panel mb-lg\"><div class=\"panel-header\">When to Use</div><div class=\"panel-body\" style=\"padding:16px;line-height:1.6;color:var(--text-secondary)\">'+escHtml(whenUse)+'</div></div>':'')+(content?'<div class=\"panel mb-lg\"><div class=\"panel-header\">Skill Content</div><div class=\"panel-body\" style=\"padding:16px;max-height:600px;overflow-y:auto;font-size:13px;line-height:1.7;color:var(--text-primary)\">'+renderMd(content)+'</div></div>':'')+approveBtns+'<div class=\"panel mb-lg\"><div class=\"panel-header\">Sessions</div><div class=\"panel-body\" style=\"padding:12px 16px\">'+sidList+'</div></div><div class=\"panel\"><div class=\"panel-header\">Details</div><div class=\"panel-body\" style=\"font-size:11px;color:var(--text-muted);padding:12px 16px\"><div>Created: '+(s.created_at||'N/A')+'</div><div>Last Used: '+(s.last_used||'N/A')+'</div></div></div></div>'}).catch(()=>{alert('Skill not found');navigate('evolution')})}
async function approveSkill(name){try{const r=await fetch(API+'/evolution/approve/'+encodeURIComponent(name),{method:'POST'});const d=await r.json();alert('Approved: '+d.status);viewEvolutionSkill(name)}catch(e){alert('Failed: '+e.message)}}
async function rejectSkill(name){try{const r=await fetch(API+'/evolution/reject/'+encodeURIComponent(name),{method:'POST'});const d=await r.json();alert('Rejected: '+d.status);navigate('evolution')}catch(e){alert('Failed: '+e.message)}}

// ── Hotspots ──
async function loadHotspots(){try{const d=await fetchJSON(API+'/hotspots?limit=50');const mw=Math.max(...d.map(x=>x.writes||0),1);$('#main').innerHTML='<div class="content"><div class="page-title">🔥 File Hotspots</div><div class="page-subtitle">Most frequently modified files with churn breakdown</div><div class="panel"><div class="panel-header">Files<span class="count">'+d.length+'</span></div><div class="panel-body"><table><tr><th>File</th><th>Reads</th><th>Writes</th><th>Deletes</th><th>Sessions</th><th>Projects</th><th>Churn</th><th>Last</th></tr>'+d.map(f=>'<tr><td class="text-xs">'+escHtml((f.path||f.file_path||'').split('/').slice(-2).join('/'))+'</td><td>'+fmtNum(f.reads)+'</td><td><strong>'+fmtNum(f.writes)+'</strong></td><td>'+fmtNum(f.deletes)+'</td><td>'+fmtNum(f.sessions_touched)+'</td><td>'+fmtNum(f.projects)+'</td><td><div style="width:'+Math.round((f.writes||0)/mw*100)+'px;height:4px;background:var(--accent);border-radius:2px"></div></td><td class="text-xs text-muted">'+(f.last_touched||'').slice(0,10)+'</td></tr>').join('')||'<tr><td colspan="8" class="text-muted">No file data</td></tr>'+'</table></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'</div></div>'}}

// ── Errors ──
async function loadErrors(){try{const d=await fetchJSON(API+'/errors');const se=d.session_errors||[];const te=d.tool_errors||[];$('#main').innerHTML='<div class="content"><div class="page-title">⚠ Error Tracking</div><div class="page-subtitle">Tool errors and problematic sessions</div><div class="grid-2 mb-lg"><div class="panel"><div class="panel-header">Tool Errors<span class="count">'+te.length+'</span></div><div class="panel-body" style="max-height:400px;overflow-y:auto"><table><tr><th>Tool</th><th>Errors</th></tr>'+(te.map(e=>'<tr><td><span class="tag tag-tool">'+escHtml(e.tool)+'</span></td><td><span class="value red">'+fmtNum(e.error_count)+'</span></td></tr>').join('')||'<tr><td colspan="2" class="text-muted">No errors detected</td></tr>')+'</table></div></div><div class="panel"><div class="panel-header">Error-Prone Sessions<span class="count">'+se.length+'</span></div><div class="panel-body" style="max-height:400px;overflow-y:auto"><table><tr><th>Session</th><th>Project</th><th>Errors</th><th>Date</th></tr>'+se.map(s=>'<tr><td><span class="clickable text-xs" onclick="viewSession(\''+escHtml(s.id)+'\')">'+shortId(s.id,16)+'</span></td><td>'+escHtml(s.project||'-')+'</td><td><span class="value red">'+fmtNum(s.error_count||0)+'</span></td><td class="text-xs text-muted">'+(s.created_at||'').slice(0,10)+'</td></tr>').join('')||'<tr><td colspan="4" class="text-muted">No error-prone sessions</td></tr>'+'</table></div></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'</div></div>'}}

// ── Memory Control ──
async function loadMemory(){try{const s=await fetchJSON(API+'/memory-stats');const p=await fetchJSON(API+'/evolution/pending');const covPct=s.summary_coverage_pct||0;const covColor=covPct>50?'green':covPct>20?'yellow':'red';$('#main').innerHTML='<div class="content"><div class="page-title">◎ Memory Control</div><div class="page-subtitle">Memory platform health, circuit breaker, and control actions</div><div class="stat-grid"><div class="stat-card"><div class="label">Skills</div><div class="value blue">'+fmtNum(s.skills_count)+'</div><div class="sub">registered</div></div><div class="stat-card"><div class="label">Knowledge</div><div class="value green">'+fmtNum(s.knowledge_count)+'</div><div class="sub">entries</div></div><div class="stat-card"><div class="label">Summaries</div><div class="value">'+fmtNum(s.summaries_count)+'</div><div class="sub">sessions</div></div><div class="stat-card"><div class="label">Coverage</div><div class="value '+covColor+'">'+covPct+'%</div><div class="sub">summarized</div></div><div class="stat-card"><div class="label">Pending Review</div><div class="value '+(p.length>0?'yellow':'green')+'">'+fmtNum(p.length)+'</div><div class="sub">items</div></div></div><div class="grid-2 mb-lg"><div class="panel"><div class="panel-header">Actions</div><div class="panel-body" style="display:flex;flex-direction:column;gap:8px;padding:12px 16px"><button class="btn btn-primary" onclick="memAction(\'refresh\')">🔄 Refresh Snapshot</button><button class="btn btn-warning" onclick="memAction(\'reset-circuit\')">⚡ Reset Circuit</button><button class="btn" onclick="navigate(\'quality\')">📋 Review Pending ('+p.length+')</button></div></div><div class="panel"><div class="panel-header">Storage</div><div class="panel-body" style="padding:12px 16px;font-size:11px;color:var(--text-secondary)"><div>Skills: '+fmtNum(s.skills_count)+' | Knowledge: '+fmtNum(s.knowledge_count)+' | Summaries: '+fmtNum(s.summaries_count)+'</div><div class="mt-sm">Summary Coverage: '+covPct+'% — run <code>coworker memory train</code> to improve</div></div></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'. Is mem0 configured?</div></div>'}}
async function memAction(a){try{const r=await fetch(API+'/memory/'+a,{method:'POST'});const d=await r.json();alert(a+': '+d.status);loadMemory()}catch(e){alert('Failed: '+e.message)}}

// ── Cost & Tokens ──
async function loadCost(){try{const d=await fetchJSON(API+'/cost-analytics');$('#main').innerHTML='<div class="content"><div class="page-title">💰 Cost & Token Analytics</div><div class="page-subtitle">Token consumption, cost, and cache efficiency per model</div><div class="stat-grid">'+(d.model_stats||[]).map(m=>{const cachePct=m.cache_hit_rate_pct||0;const cacheColor=cachePct>80?'green':cachePct>50?'yellow':'red';return'<div class="stat-card"><div class="label">'+escHtml(m.model||'unknown')+'</div><div class="value blue">$'+(m.total_cost||0)+'</div><div class="sub">'+fmtNum(m.total_input)+'→'+fmtNum(m.total_output)+' tokens | '+m.sessions+' sessions</div><div class="sub"><span class="'+cacheColor+'">📊 Cache: '+cachePct+'% hit</span> ('+fmtNum(m.total_cache_read||0)+' read / '+fmtNum(m.total_cache_write||0)+' write)</div></div>'}).join('')+'</div><div class="panel"><div class="panel-header">Daily Token Usage (30 days)</div><div class="panel-body" style="max-height:400px;overflow-y:auto"><table><tr><th>Day</th><th>Sessions</th><th>Input</th><th>Output</th><th>Total</th></tr>'+((d.daily_tokens||[]).map(r=>'<tr><td>'+r.day+'</td><td>'+r.sessions+'</td><td>'+fmtNum(r.input_tokens)+'</td><td>'+fmtNum(r.output_tokens)+'</td><td><strong>'+fmtNum((r.input_tokens||0)+(r.output_tokens||0))+'</strong></td></tr>').join('')||'<tr><td colspan="5" class="text-muted">No token data</td></tr>')+'</table></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'</div></div>'}}

// ── Efficiency ──
async function loadEfficiency(){try{const d=await fetchJSON(API+'/efficiency');$('#main').innerHTML='<div class="content"><div class="page-title">📊 Efficiency Insights</div><div class="page-subtitle">Session efficiency scores and bottlenecks ('+d.total_summaries+' summarized)</div><div class="stat-grid"><div class="stat-card"><div class="label">Avg Efficiency</div><div class="value '+(d.avg_efficiency>=7?'green':d.avg_efficiency>=5?'yellow':'red')+'">'+(d.avg_efficiency||0)+'/10</div></div><div class="stat-card"><div class="label">Think/Action Ratio</div><div class="value">'+(d.avg_think_action||0)+'</div></div><div class="stat-card"><div class="label">Edit Redundancy</div><div class="value">'+(d.avg_edit_redundancy||0)+'</div></div><div class="stat-card"><div class="label">Total Analyzed</div><div class="value blue">'+d.total_summaries+'</div><div class="sub">sessions</div></div></div><div class="grid-2 mb-lg"><div class="panel"><div class="panel-header">Top Bottlenecks</div><div class="panel-body"><table><tr><th>Bottleneck</th><th>Count</th></tr>'+((d.bottlenecks||[]).map(b=>'<tr><td>'+escHtml(b.bottlenecks)+'</td><td><span class="tag tag-skill">'+b.count+'</span></td></tr>').join('')||'<tr><td colspan="2" class="text-muted">No bottleneck data</td></tr>')+'</table></div></div><div class="panel"><div class="panel-header">Recent Summaries</div><div class="panel-body" style="max-height:400px;overflow-y:auto">'+((d.recent||[]).map(s=>'<div style="padding:8px 12px;border-bottom:1px solid var(--border);font-size:11px"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span class="tag tag-knowledge">Score: '+(s.efficiency_score||'?')+'/10</span><span class="text-xs text-muted">'+shortId(s.session_id,16)+'</span></div>'+(s.bottlenecks?'<div class="text-xs" style="color:var(--yellow)">⚠ '+escHtml(s.bottlenecks)+'</div>':'')+(s.efficiency_tip?'<div class="text-xs" style="color:var(--green)">💡 '+escHtml(s.efficiency_tip)+'</div>':'')+'</div>').join('')||'<div class="text-muted" style="padding:12px">No summaries yet.</div>')+'</div></div></div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'</div></div>'}}

// ── Data Quality ──
async function loadQuality(){try{const d=await fetchJSON(API+'/data-quality');function bar(pct){return'<div style="display:flex;align-items:center;gap:8px"><div style="flex:1;height:6px;background:var(--bg-tertiary);border-radius:3px"><div style="width:'+pct+'%;height:6px;background:'+(pct>80?'var(--green)':pct>40?'var(--yellow)':'var(--red)')+';border-radius:3px"></div></div><span style="font-size:10px;color:'+(pct>80?'var(--green)':pct>40?'var(--yellow)':'var(--red)')+'">'+pct+'%</span></div>'}$('#main').innerHTML='<div class="content"><div class="page-title">🔍 Data Quality</div><div class="page-subtitle">Coverage rates for '+fmtNum(d.total_sessions)+' total sessions</div><div class="panel"><div class="panel-header">Coverage Metrics</div><div class="panel-body" style="padding:16px"><table><tr><th>Metric</th><th>Covered</th><th>Missing</th><th>Rate</th></tr><tr><td>Project</td><td>'+fmtNum(d.project.covered)+'</td><td>'+fmtNum(d.project.missing)+'</td><td>'+bar(d.project.pct)+'</td></tr><tr><td>Initiative</td><td>'+fmtNum(d.initiative.covered)+'</td><td>'+fmtNum(d.initiative.missing)+'</td><td>'+bar(d.initiative.pct)+'</td></tr><tr><td>Closed Tracking</td><td>'+fmtNum(d.closed.covered)+'</td><td>'+fmtNum(d.closed.missing)+'</td><td>'+bar(d.closed.pct)+'</td></tr><tr><td>Tokens</td><td>'+fmtNum(d.tokens.covered)+'</td><td>'+fmtNum(d.tokens.missing)+'</td><td>'+bar(d.tokens.pct)+'</td></tr><tr><td>Summaries</td><td>'+fmtNum(d.summaries.covered)+'</td><td>'+fmtNum(d.summaries.missing)+'</td><td>'+bar(d.summaries.pct)+'</td></tr></table></div></div><div class="text-xs text-muted mt-sm" style="padding:8px 16px">💡 Run <code>coworker memory train</code> to backfill summaries and tokens.</div></div>'}catch(e){$('#main').innerHTML='<div class="content"><div class="error">Failed: '+e.message+'</div></div>'}}

// INIT
renderTopbar();navigate('summary');
