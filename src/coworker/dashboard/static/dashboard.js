const API = '/api';
let currentView = 'overview';
let currentData = {};

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function renderSidebar() {
  const views = [
    {id:'overview',label:'Overview',icon:'◉',section:'Analytics'},
    {id:'sessions',label:'Sessions',icon:'☰',section:'Analytics'},
    {id:'monitor',label:'Monitor',icon:'◉',section:'Monitoring'},
    {id:'skills',label:'Skills',icon:'◆',section:'Monitoring'},
    {id:'tools',label:'Tools',icon:'⚙',section:'Monitoring'},
    {id:'files',label:'Files',icon:'◫',section:'Monitoring'},
    {id:'knowledge',label:'Knowledge',icon:'◎',section:'Analytics'},
    {id:'initiatives',label:'Initiatives',icon:'◈',section:'Analytics'},
  ];
  let html='<div class="sidebar-header"><span class="icon">⧩</span> Coworker</div>';
  let lastSection='';
  views.forEach(v=>{
    if(v.section!==lastSection){
      html+=`<div class="nav-section"><div class="nav-label">${v.section}</div>`;
      lastSection=v.section;
    }
    html+=`<div class="nav-item${v.id===currentView?' active':''}" onclick="navigate('${v.id}')">${v.icon} ${v.label}</div>`;
  });
  document.getElementById('sidebar').innerHTML=html;
}

function navigate(view) {
  currentView = view;
  renderSidebar();
  document.getElementById('main').innerHTML='<div class="content"><div class="loading">Loading...</div></div>';
  const loaders={overview:loadOverview,sessions:loadSessions,skills:loadSkills,monitor:loadMonitor,tools:loadTools,files:loadFiles,knowledge:loadKnowledge,initiatives:loadInitiatives};
  (loaders[view]||loadOverview)();
}

async function loadOverview() {
  const data=await fetchJSON(`${API}/overview`);
  const {total_sessions,total_messages,total_tools,total_skills,total_knowledge,active_sessions,tool_distribution,daily_sessions,recent_sessions}=data;
  const maxDaily=Math.max(...daily_sessions.map(d=>d.c),1);
  document.getElementById('main').innerHTML=`
    <div class="content">
      <div class="page-title">Analytics Overview</div>
      <div class="page-subtitle">Real-time session monitoring and historical analysis</div>
      <div class="stat-grid">
        <div class="stat-card"><div class="label">Total Sessions</div><div class="value blue">${total_sessions}</div><div class="sub">${active_sessions} active now</div></div>
        <div class="stat-card"><div class="label">Messages</div><div class="value">${total_messages.toLocaleString()}</div></div>
        <div class="stat-card"><div class="label">Tool Calls</div><div class="value green">${total_tools.toLocaleString()}</div></div>
        <div class="stat-card"><div class="label">Skills Used</div><div class="value red">${total_skills}</div></div>
        <div class="stat-card"><div class="label">Knowledge Cards</div><div class="value purple">${total_knowledge}</div></div>
      </div>
      <div class="grid-2 mb-lg">
        <div class="panel"><div class="panel-header">Daily Sessions</div>
          <div class="chart-bar-group">${daily_sessions.map(d=>`<div class="chart-bar" style="height:${(d.c/maxDaily)*70+5}px"><span class="tip">${d.day.slice(5)}: ${d.c}</span></div>`).join('')}</div>
          <div style="display:flex;justify-content:space-between;padding:4px 16px 8px;font-size:9px;color:var(--text-muted)">${daily_sessions.map(d=>`<span>${d.day.slice(5)}</span>`).join('')}</div>
        </div>
        <div class="panel"><div class="panel-header">Tool Distribution</div>
          <div class="panel-body" style="padding:12px 16px">${tool_distribution.map((t,i)=>{
            const w=(t.c/Math.max(...tool_distribution.map(x=>x.c)))*100;
            return `<div class="flex flex-between mb-sm"><span class="tag tag-tool">${t.tool}</span><div style="flex:1;margin:0 12px"><div class="bar"><div class="bar-fill" style="width:${w}%"></div></div></div><span class="text-sm text-muted">${t.c}</span></div>`;
          }).join('')}</div>
        </div>
      </div>
      <div class="panel"><div class="panel-header">Recent Sessions<span class="count">${recent_sessions.length}</span></div>
        <div class="panel-body"><table><tr><th>Session</th><th>IDE</th><th>Project</th><th>Initiative</th><th>Msgs</th><th>Tools</th><th>Started</th></tr>
          ${recent_sessions.map(s=>`<tr><td><span class="clickable" onclick="viewSession('${s.id}')">${(s.id||'').slice(0,20)}</span></td><td>${s.ide||'-'}</td><td>${s.project||'-'}</td><td>${s.initiative?`<span class="tag tag-session">${s.initiative}</span>`:'-'}</td><td>${s.message_count||0}</td><td>${s.tool_count||0}</td><td class="text-sm text-muted">${(s.created_at||'').slice(0,16)}</td></tr>`).join('')}
        </table></div></div>
    </div>`;
}

async function loadSessions() {
  const data=await fetchJSON(`${API}/sessions?limit=100`);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Sessions</div><div class="page-subtitle">All recorded AI coding sessions</div>
      <div class="panel"><div class="panel-body"><table><tr><th>Session ID</th><th>IDE</th><th>Project</th><th>Initiative</th><th>Msgs</th><th>Tools</th><th>Duration</th><th>Started</th></tr>
        ${data.map(s=>`<tr><td><span class="clickable" onclick="viewSession('${s.id}')">${(s.id||'').slice(0,24)}</span></td><td>${s.ide||'-'}</td><td>${s.project||'-'}</td><td>${s.initiative?`<span class="tag tag-session">${s.initiative}</span>`:'-'}</td><td>${s.message_count||0}</td><td>${s.tool_count||0}</td><td>${s.duration_min?s.duration_min+'m':'-'}</td><td class="text-sm text-muted">${(s.created_at||'').slice(0,16)}</td></tr>`).join('')}
        </table></div></div></div>`;
}

async function loadMonitor() {
  const [overview, skills, topFiles]=await Promise.all([
    fetchJSON(`${API}/overview`),
    fetchJSON(`${API}/skills`),
    fetchJSON(`${API}/top-files?limit=30`),
  ]);
  const maxSkill=Math.max(...skills.map(s=>s.total_calls),1);
  const maxFile=Math.max(...topFiles.map(f=>f.total_ops),1);
  document.getElementById('main').innerHTML=`
    <div class="content">
      <div class="page-title">Session Monitor</div>
      <div class="page-subtitle">What the AI does — real-time task, file, and skill tracking</div>
      <div class="stat-grid">
        <div class="stat-card"><div class="label">Active Sessions</div><div class="value blue">${overview.active_sessions}</div><div class="sub">${overview.total_sessions} total</div></div>
        <div class="stat-card"><div class="label">Tool Calls</div><div class="value green">${overview.total_tools.toLocaleString()}</div></div>
        <div class="stat-card"><div class="label">Skills</div><div class="value red">${overview.total_skills}</div><div class="sub">${skills.reduce((a,s)=>a+s.total_calls,0)} invocations</div></div>
        <div class="stat-card"><div class="label">Files Touched</div><div class="value yellow">${topFiles.length}</div><div class="sub">${topFiles.reduce((a,f)=>a+f.total_ops,0)} ops</div></div>
      </div>
      <div class="grid-2 mb-lg">
        <div class="panel"><div class="panel-header">Top Skills<span class="count">by calls</span></div>
          <div class="panel-body" style="padding:8px 16px">${skills.slice(0,15).map(s=>`<div class="flex flex-between mb-sm"><span class="tag tag-skill">${s.name}</span><div style="flex:1;margin:0 8px"><div class="bar"><div class="bar-fill" style="width:${(s.total_calls/maxSkill)*100}%;background:var(--red)"></div></div></div><span class="text-xs text-muted">${s.total_calls}</span></div>`).join('')}</div>
        </div>
        <div class="panel"><div class="panel-header">Top Files<span class="count">by ops</span></div>
          <div class="panel-body" style="padding:8px 16px;max-height:360px;overflow-y:auto">${topFiles.slice(0,30).map(f=>{
            const name=(f.file_path||'').split('/').pop()||f.file_path;
            return `<div class="flex flex-between mb-sm"><div style="flex:1;overflow:hidden"><span class="text-xs text-monospace" title="${f.file_path}">${name}</span></div><span class="tag tag-file">r${f.reads||0} w${f.writes||0}</span><div style="width:80px;margin-left:8px"><div class="bar"><div class="bar-fill" style="width:${(f.total_ops/maxFile)*100}%"></div></div></div><span class="text-xs text-muted">${f.total_ops}</span></div>`;
          }).join('')}</div>
        </div>
      </div>
      <div class="panel"><div class="panel-header">Recent Sessions<span class="count">click to view timeline</span></div>
        <div class="panel-body"><table><tr><th>Session</th><th>IDE</th><th>Project</th><th>Initiative</th><th>Msgs</th><th>Tools</th><th>Started</th></tr>
          ${overview.recent_sessions.map(s=>`<tr><td><span class="clickable" onclick="viewSession('${s.id}')">${(s.id||'').slice(0,20)}</span></td><td>${s.ide||'-'}</td><td>${s.project||'-'}</td><td>${s.initiative?`<span class="tag tag-session">${s.initiative}</span>`:'-'}</td><td>${s.message_count||0}</td><td>${s.tool_count||0}</td><td class="text-sm text-muted">${(s.created_at||'').slice(0,16)}</td></tr>`).join('')}
        </table></div></div>
    </div>`;
}

async function loadSkills() {
  const data=await fetchJSON(`${API}/skills`);
  const maxCalls=Math.max(...data.map(s=>s.total_calls),1);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Skills</div><div class="page-subtitle">AI skills invoked during sessions</div>
      <div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Total Skills</div><div class="value red">${data.length}</div></div><div class="stat-card"><div class="label">Total Invocations</div><div class="value">${data.reduce((a,s)=>a+s.total_calls,0)}</div></div></div>
      <div class="panel"><div class="panel-body"><table><tr><th>Skill</th><th>Usage</th><th>Calls</th></tr>
        ${data.map(s=>`<tr><td><span class="tag tag-skill">${s.name}</span></td><td><div class="bar" style="width:200px"><div class="bar-fill" style="width:${(s.total_calls/maxCalls)*100}%;background:var(--red)"></div></div></td><td>${s.total_calls}</td></tr>`).join('')}
        </table></div></div></div>`;
}

async function loadTools() {
  const data=await fetchJSON(`${API}/tools`);
  const maxCalls=Math.max(...data.map(t=>t.calls),1);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Tools</div><div class="page-subtitle">All tool invocations across sessions</div>
      <div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Total Calls</div><div class="value blue">${data.reduce((a,t)=>a+t.calls,0)}</div></div><div class="stat-card"><div class="label">Unique Tools</div><div class="value">${data.length}</div></div><div class="stat-card"><div class="label">Avg Duration</div><div class="value green">${Math.round(data.reduce((a,t)=>a+(t.avg_ms||0),0)/Math.max(data.length,1))}ms</div></div></div>
      <div class="panel"><div class="panel-body"><table><tr><th>Tool</th><th>Type</th><th>Usage</th><th>Calls</th><th>Avg (ms)</th></tr>
        ${data.map(t=>`<tr><td><span class="tag tag-tool">${t.tool}</span></td><td>${t.tool_type||'builtin'}${t.server_name?' ('+t.server_name+')':''}</td><td><div class="bar" style="width:160px"><div class="bar-fill" style="width:${(t.calls/maxCalls)*100}%"></div></div></td><td>${t.calls}</td><td>${t.avg_ms||'-'}</td></tr>`).join('')}
        </table></div></div></div>`;
}

async function loadFiles() {
  const data=await fetchJSON(`${API}/top-files?limit=100`);
  const maxOps=Math.max(...data.map(f=>f.total_ops),1);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Files</div><div class="page-subtitle">Files read/written across all sessions</div>
      <div class="stat-grid mb-lg"><div class="stat-card"><div class="label">Files Touched</div><div class="value green">${data.length}</div></div><div class="stat-card"><div class="label">Total Reads</div><div class="value">${data.reduce((a,f)=>a+(f.reads||0),0)}</div></div><div class="stat-card"><div class="label">Total Writes+Edits</div><div class="value yellow">${data.reduce((a,f)=>a+(f.writes||0),0)}</div></div></div>
      <div class="panel"><div class="panel-body"><table><tr><th>File</th><th>Reads</th><th>Writes</th><th>Total</th><th>Projects</th></tr>
        ${data.map(f=>`<tr><td class="text-monospace" title="${f.file_path}">${(f.file_path||'').slice(-60)}</td><td>${f.reads||0}</td><td>${f.writes||0}</td><td><div class="flex"><div class="bar" style="width:80px"><div class="bar-fill" style="width:${(f.total_ops/maxOps)*100}%"></div></div><span class="text-xs" style="margin-left:6px">${f.total_ops}</span></div></td><td class="text-xs text-muted">${(f.projects||'').slice(0,40)}</td></tr>`).join('')}
        </table></div></div></div>`;
}

async function loadKnowledge() {
  const data=await fetchJSON(`${API}/knowledge`);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Knowledge Cards</div><div class="page-subtitle">LLM-generated insights and patterns</div>
      ${data.length===0?'<div class="panel"><div class="panel-body" style="padding:24px;text-align:center;color:var(--text-muted)">No knowledge cards yet.</div></div>':''}
      ${data.map(k=>`<div class="panel"><div class="panel-header"><span class="tag tag-knowledge">${k.type||'unknown'}</span> ${k.title}<span class="count">${(k.generated_at||'').slice(0,10)}</span></div><div class="panel-body" style="padding:16px"><div class="text-sm" style="margin-bottom:8px">${k.summary||''}</div><div class="flex gap-sm"><span class="text-xs text-muted">Session:</span><span class="text-xs text-monospace">${(k.session_id||'').slice(0,20)}</span></div></div></div>`).join('')}
    </div>`;
}

async function loadInitiatives() {
  const data=await fetchJSON(`${API}/initiatives`);
  document.getElementById('main').innerHTML=`
    <div class="content"><div class="page-title">Initiatives</div><div class="page-subtitle">Cross-session workstreams</div>
      ${data.length===0?'<div class="panel"><div class="panel-body" style="padding:24px;text-align:center;color:var(--text-muted)">No initiatives tracked.</div></div>':`<div class="panel"><div class="panel-body"><table><tr><th>Initiative</th><th>Project</th><th>Sessions</th><th>Tool Calls</th></tr>${data.map(i=>`<tr><td><span class="tag tag-session">${i.initiative}</span></td><td>${i.project||'-'}</td><td>${i.session_count}</td><td>${i.tool_count}</td></tr>`).join('')}</table></div></div>`}
    </div>`;
}

async function viewSession(id) {
  const [detail, timeline]=await Promise.all([
    fetchJSON(`${API}/sessions/${id}`),
    fetchJSON(`${API}/sessions/${id}/timeline`).catch(()=>[]),
  ]);
  const s=detail.session;
  const summary=detail.summary;
  document.getElementById('main').innerHTML=`
    <div class="content">
      <div class="flex flex-between mb-lg"><div><div class="page-title">${(s.id||'').slice(0,24)}...</div><div class="page-subtitle"><span class="tag tag-tool">${s.ide||'?'}</span>${s.project?` <span class="tag tag-file">${s.project}</span>`:''}${s.initiative?` <span class="tag tag-knowledge">${s.initiative}</span>`:''}</div></div><span class="clickable" onclick="navigate('sessions')">← Back</span></div>
      <div class="stat-grid" style="grid-template-columns:repeat(auto-fit,minmax(100px,1fr))"><div class="stat-card"><div class="label">Msgs</div><div class="value" style="font-size:24px">${detail.messages.length}</div></div><div class="stat-card"><div class="label">Tools</div><div class="value blue" style="font-size:24px">${detail.tool_calls.length}</div></div><div class="stat-card"><div class="label">Files</div><div class="value green" style="font-size:24px">${detail.file_ops.length}</div></div>${detail.stats?`<div class="stat-card"><div class="label">Skills</div><div class="value red" style="font-size:24px">${detail.stats.skill_count||0}</div></div><div class="stat-card"><div class="label">Bash</div><div class="value yellow" style="font-size:24px">${detail.stats.bash_count||0}</div></div>`:''}</div>
      ${summary?`<div class="panel mb-lg"><div class="panel-header">AI Summary</div><div class="panel-body" style="padding:16px"><div class="grid-2"><div class="summary-card"><div class="label">Context</div><div class="text">${summary.context_to_remember||'-'}</div></div><div class="summary-card"><div class="label">Tip</div><div class="text">${summary.efficiency_tip||'-'}</div></div><div class="summary-card"><div class="label">Keywords</div><div class="text">${summary.memory_keywords||'-'}</div></div><div class="summary-card"><div class="label">Score</div><div class="text" style="font-size:20px;font-weight:700;color:${(summary.efficiency_score||0)>0.6?'var(--green)':'var(--yellow)'}">${summary.efficiency_score?Math.round(summary.efficiency_score*100)+'%':'-'}</div></div></div></div></div>`:''}
      <div class="panel"><div class="panel-header">Timeline<span class="count">${timeline.length} events — what happened, in order</span></div>
        <div class="panel-body" style="max-height:600px;overflow-y:auto">${timeline.map(e=>{
          const icons={message:{u:'📝',a:'🤖'},tool_call:{Task:'🔧',Bash:'💻',Read:'📖',Write:'✏️',Edit:'🖊',Glob:'🔍',WebFetch:'🌐',Skill:'⚡',WebSearch:'🔎',Grep:'🔎',TodoWrite:'✅',TaskOutput:'📤',default:'🔧'},file_op:{read:'📖',write:'✏️',edit:'🖊',delete:'🗑',default:'◫'}};
          let icon='•',cls='';
          if(e.kind==='message'){icon=icons.message[e.subtype]||'💬';cls=e.subtype==='user'?'tag-skill':'tag-tool';}
          else if(e.kind==='tool_call'){icon=(icons.tool_call[e.tool]||icons.tool_call[e.subtype]||icons.tool_call.default);cls='tag-tool';}
          else if(e.kind==='file_op'){icon=(icons.file_op[e.subtype]||icons.file_op.default);cls='tag-file';}
          const detail=(e.detail||'').slice(0,120);
          const time=(e.ts||'').slice(11,19);
          return `<div style="padding:4px 16px;border-bottom:1px solid var(--border);font-size:12px;display:flex;align-items:center;gap:8px"><span style="width:40px;text-align:center">${icon}</span><span class="tag ${cls}">${e.tool||e.subtype||e.kind}</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-secondary)">${detail}</span><span class="text-xs text-muted">${time}</span></div>`;
        }).join('')||'<div style="padding:24px;text-align:center;color:var(--text-muted)">No timeline events recorded.</div>'}</div></div>
    </div>`;
}

renderSidebar();
loadOverview();
