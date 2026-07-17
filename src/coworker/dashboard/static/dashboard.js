const API = '/api';
let currentView = 'overview';
let viewHistory = [];

async function fetchJSON(url) { const r=await fetch(url); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
function $(s) { return document.querySelector(s); }
function $$(s) { return document.querySelectorAll(s); }

function renderSidebar() {
  const views = [
    {id:'overview',label:'Overview',icon:'◉',section:'Analytics'},
    {id:'projects',label:'Projects',icon:'◫',section:'Analytics'},
    {id:'sessions',label:'Sessions',icon:'☰',section:'Analytics'},
    {id:'models',label:'Models',icon:'⚙',section:'Monitoring'},
    {id:'skills',label:'Skills',icon:'⚡',section:'Monitoring'},
    {id:'tools',label:'Tools',icon:'🔧',section:'Monitoring'},
    {id:'files',label:'Files',icon:'📁',section:'Monitoring'},
    {id:'knowledge',label:'Knowledge',icon:'✓',section:'Analytics'},
    {id:'initiatives',label:'Initiatives',icon:'📋',section:'Analytics'},
  ];
  let html='<div class="sidebar-header"><span class="icon">◆</span> Coworker</div>';
  let ls='';
  views.forEach(v => {
    if(v.section!==ls){html+=`<div class="nav-section"><div class="nav-label">${v.section}</div>`;ls=v.section;}
    html+=`<div class="nav-item${v.id===currentView?' active':''}" onclick="navigate('${v.id}')">${v.icon} ${v.label}</div>`;
  });
  $('#sidebar').innerHTML=html;
}

function navigate(view,ph=true){if(ph&&currentView!==view)viewHistory.push(currentView);currentView=view;renderSidebar();
  $('#main').innerHTML='<div class="content"><div class="loading"><div class="spinner"></div><span>Loading...</span></div></div>';
  const l={overview:loadOverview,projects:loadProjects,sessions:loadSessions,models:loadModels,skills:loadSkills,tools:loadTools,files:loadFiles,knowledge:loadKnowledge,initiatives:loadInitiatives};(l[view]||loadOverview)();
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
  const d=await fetchJSON(API+'/projects');const mS=Math.max(...d.map(x=>x.session_count),1);
  $('#main').innerHTML='<div class="content"><div class="page-title">Projects</div><div class="page-subtitle">Work across projects with worktree merging</div>'
  +'<div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Projects</div><div class="value blue">'+d.length+'</div></div><div class="stat-card"><div class="label">Sessions</div><div class="value">'+d.reduce((a,x)=>a+x.session_count,0)+'</div></div><div class="stat-card"><div class="label">Tools</div><div class="value green">'+fmtNum(d.reduce((a,x)=>a+(x.total_tools||0),0))+'</div></div></div>'
  +'<div class="panel"><div class="panel-body"><table><tr><th>Project</th><th>IDE</th><th class="text-right">Sessions</th><th class="text-right">Tools</th><th class="text-right">Msg</th><th class="text-right">Tokens</th><th>Last</th><th></th></tr>'
  +d.map(x=>expRow('<td><span class="tag '+(x.project_name==='root'?'tag-skill':'tag-file')+'">'+x.project_name+'</span></td><td>'+ideTags(x.ides)+'</td><td class="text-right">'+x.session_count+'</td><td class="text-right">'+(x.total_tools||0)+'</td><td class="text-right">'+(x.total_messages||0)+'</td><td class="text-right">'+((x.total_tokens_in||0)+(x.total_tokens_out||0))+'</td><td class="text-sm text-muted">'+fmtTime(x.last_session)+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading sessions...</span></div>','project:'+x.project_name)).join('')
  +'</table></div></div></div>';
}

// SESSIONS
let sCache=[],sF={id:'',ide:'',project:'',initiative:''};
function pName(x){return x.project||(x.cwd?x.cwd.split('/').pop()||x.cwd:'-');}
function applySF(){document.querySelectorAll('.sess-filter').forEach(i=>sF[i.dataset.key]=i.value.toLowerCase());
  const f=sCache.filter(x=>(!sF.id||(x.id||'').toLowerCase().includes(sF.id))&&(!sF.ide||(x.ide||'').toLowerCase().includes(sF.ide))&&(!sF.project||(pName(x).toLowerCase().includes(sF.project))&&(!sF.initiative||(x.initiative||'').toLowerCase().includes(sF.initiative))));
  document.getElementById('sBody').innerHTML=f.map(x=>expRow('<td><span class="clickable text-monospace text-xs">'+shortId(x.id,22)+'</span></td><td>'+ideIconHtml(x.ide)+'</td><td>'+pName(x)+(x.project?'':' <span class="text-xs text-muted" style="font-size:9px">from cwd</span>')+'</td><td>'+(x.initiative?'<span class="tag tag-session">'+x.initiative+'</span>':'-')+'</td><td class="text-right">'+(x.message_count||0)+'</td><td class="text-right">'+(x.tool_count||0)+'</td><td class="text-right">'+(x.duration_min?x.duration_min+'m':'-')+'</td><td class="text-sm text-muted">'+fmtTime(x.created_at)+'</td>','<div class="loading" style="padding:20px"><div class="spinner"></div><span>Loading...</span></div>',x.id)).join('');}
async function loadSessions(){const d=await fetchJSON(API+'/sessions?limit=500');sCache=d;renderS(d);}
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

// AUTO-REFRESH
let ri=null;
function startAR(view,ms){if(ri)clearInterval(ri);ri=setInterval(()=>{if(document.hidden)return;if(view==='overview')loadOverview();},ms);}
const _n=navigate;navigate=function(view,ph){if(ri)clearInterval(ri);_n(view,ph);if(view==='overview')startAR(view,15000);};

// INIT
renderSidebar();loadOverview();startAR('overview',15000);
