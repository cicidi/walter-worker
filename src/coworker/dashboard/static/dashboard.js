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
    {id:'overview',label:'Overview',icon:'◉'},
    {id:'sessions',label:'Sessions',icon:'☰'},
    {id:'skills',label:'Skills',icon:'◆'},
    {id:'tools',label:'Tools',icon:'⚙'},
    {id:'files',label:'Files',icon:'◫'},
    {id:'knowledge',label:'Knowledge',icon:'◎'},
    {id:'initiatives',label:'Initiatives',icon:'◈'},
  ];
  document.getElementById('sidebar').innerHTML = `
    <div class="sidebar-header">
      <span class="icon">⧩</span> Coworker
    </div>
    <div class="nav-section">
      <div class="nav-label">Analytics</div>
      ${views.map(v=>`<div class="nav-item${v.id===currentView?' active':''}" onclick="navigate('${v.id}')">${v.icon} ${v.label}</div>`).join('')}
    </div>`;
}

function navigate(view) {
  currentView = view;
  renderSidebar();
  document.getElementById('main').innerHTML = '<div class="content"><div class="loading">Loading...</div></div>';
  const loaders = {
    overview:loadOverview, sessions:loadSessions, skills:loadSkills,
    tools:loadTools, files:loadFiles, knowledge:loadKnowledge, initiatives:loadInitiatives
  };
  (loaders[view]||loadOverview)();
}

async function loadOverview() {
  const data = await fetchJSON(`${API}/overview`);
  currentData = data;
  const {total_sessions,total_messages,total_tools,total_skills,total_knowledge,active_sessions,tool_distribution,daily_sessions,recent_sessions} = data;
  const maxDaily = Math.max(...daily_sessions.map(d=>d.c),1);
  document.getElementById('main').innerHTML = `
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
        <div class="panel"><div class="panel-header">Daily Sessions<span class="count">Last 14 days</span></div>
          <div class="chart-bar-group">
            ${daily_sessions.map(d=>`<div class="chart-bar" style="height:${(d.c/maxDaily)*70+5}px"><span class="tip">${d.day.slice(5)}: ${d.c}</span></div>`).join('')}
          </div>
          <div style="display:flex;justify-content:space-between;padding:4px 16px 8px;font-size:9px;color:var(--text-muted)">
            ${daily_sessions.map(d=>`<span>${d.day.slice(5)}</span>`).join('')}
          </div>
        </div>
        <div class="panel"><div class="panel-header">Tool Usage Distribution</div>
          <div class="panel-body" style="padding:12px 16px">
            ${tool_distribution.map((t,i)=>{
              const colors=['#3d71d9','#3eb97f','#e84d59','#ebb434','#a97fe6','#5ea1f0','#f26b4b','#7eb0d5','#b2e061','#bd7ebe'];
              const w = (t.c/Math.max(...tool_distribution.map(x=>x.c)))*100;
              return `<div class="flex flex-between mb-sm"><span class="tag tag-tool">${t.tool}</span><div style="flex:1;margin:0 12px"><div class="bar"><div class="bar-fill" style="width:${w}%;background:${colors[i%10]}"></div></div></div><span class="text-sm text-muted">${t.c}</span></div>`;
            }).join('')}
          </div>
        </div>
      </div>
      <div class="panel"><div class="panel-header">Recent Sessions<span class="count">${recent_sessions.length} sessions</span></div>
        <div class="panel-body">
          <table><tr><th>Session</th><th>IDE</th><th>Project</th><th>Branch</th><th>Initiative</th><th>Messages</th><th>Tools</th><th>Started</th></tr>
            ${recent_sessions.map(s=>`
              <tr>
                <td><span class="clickable" onclick="viewSession('${s.id}')">${(s.id||'').slice(0,22)}</span></td>
                <td>${s.ide||'-'}</td><td>${s.project||'-'}</td><td>${s.branch||'-'}</td>
                <td>${s.initiative?`<span class="tag tag-session">${s.initiative}</span>`:'-'}</td>
                <td>${s.message_count||0}</td><td>${s.tool_count||0}</td>
                <td class="text-sm text-muted">${(s.created_at||'').slice(0,16)}</td>
              </tr>`).join('')}
          </table>
        </div>
      </div>
    </div>`;
}

async function loadSessions() {
  const data = await fetchJSON(`${API}/sessions?limit=100`);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Sessions</div>
      <div class="page-subtitle">All recorded AI coding sessions</div>
      <div class="panel"><div class="panel-body">
        <table><tr><th>Session ID</th><th>IDE</th><th>Project</th><th>Branch</th><th>Initiative</th><th>Messages</th><th>Tools</th><th>Duration</th><th>Started</th></tr>
          ${data.map(s=>`
            <tr>
              <td><span class="clickable" onclick="viewSession('${s.id}')">${s.id}</span></td>
              <td>${s.ide||'-'}</td><td>${s.project||'-'}</td><td>${s.branch||'-'}</td>
              <td>${s.initiative?`<span class="tag tag-session">${s.initiative}</span>`:'-'}</td>
              <td>${s.message_count||0}</td><td>${s.tool_count||0}</td>
              <td>${s.duration_min?s.duration_min+'m':'-'}</td>
              <td class="text-sm text-muted">${(s.created_at||'').slice(0,16)}</td>
            </tr>`).join('')}
        </table>
      </div></div>
    </div>`;
}

async function loadSkills() {
  const data = await fetchJSON(`${API}/skills`);
  const maxCalls = Math.max(...data.map(s=>s.total_calls),1);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Skills</div>
      <div class="page-subtitle">AI skills invoked during sessions</div>
      <div class="stat-grid mb-lg">
        <div class="stat-card"><div class="label">Total Skills</div><div class="value red">${data.length}</div></div>
        <div class="stat-card"><div class="label">Total Invocations</div><div class="value">${data.reduce((a,s)=>a+s.total_calls,0)}</div></div>
      </div>
      <div class="panel"><div class="panel-body">
        <table><tr><th>Skill</th><th>Usage</th><th>Calls</th><th>First Invoked</th><th>Last Invoked</th></tr>
          ${data.map(s=>`
            <tr>
              <td><span class="tag tag-skill">${s.name}</span></td>
              <td><div class="bar" style="width:200px"><div class="bar-fill" style="width:${(s.total_calls/maxCalls)*100}%;background:var(--red)"></div></div></td>
              <td>${s.total_calls}</td>
              <td class="text-sm text-muted">${(s.first_invoked||'').slice(0,16)}</td>
              <td class="text-sm text-muted">${(s.last_invoked||'').slice(0,16)}</td>
            </tr>`).join('')}
        </table>
      </div></div>
    </div>`;
}

async function loadTools() {
  const data = await fetchJSON(`${API}/tools`);
  const maxCalls = Math.max(...data.map(t=>t.calls),1);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Tools</div>
      <div class="page-subtitle">All tool invocations (built-in + MCP)</div>
      <div class="stat-grid mb-lg">
        <div class="stat-card"><div class="label">Total Calls</div><div class="value blue">${data.reduce((a,t)=>a+t.calls,0)}</div></div>
        <div class="stat-card"><div class="label">Unique Tools</div><div class="value">${data.length}</div></div>
        <div class="stat-card"><div class="label">Avg Duration</div><div class="value green">${Math.round(data.reduce((a,t)=>a+(t.avg_ms||0),0)/Math.max(data.length,1))}ms</div></div>
      </div>
      <div class="panel"><div class="panel-body">
        <table><tr><th>Tool</th><th>Type</th><th>Usage</th><th>Calls</th><th>Avg (ms)</th><th>Max (ms)</th></tr>
          ${data.map(t=>`
            <tr>
              <td><span class="tag tag-tool">${t.tool}</span></td>
              <td><span class="tag ${t.tool_type==='mcp'?'tag-mcp':'tag-builtin'}">${t.tool_type||'builtin'}${t.server_name?' ('+t.server_name+')':''}</span></td>
              <td><div class="bar" style="width:160px"><div class="bar-fill" style="width:${(t.calls/maxCalls)*100}%;background:var(--blue)"></div></div></td>
              <td>${t.calls}</td>
              <td>${t.avg_ms||'-'}</td>
              <td>${t.max_ms||'-'}</td>
            </tr>`).join('')}
        </table>
      </div></div>
    </div>`;
}

async function loadFiles() {
  const data = await fetchJSON(`${API}/files`);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Files</div>
      <div class="page-subtitle">Files read/written/edited across all sessions</div>
      <div class="stat-grid mb-lg">
        <div class="stat-card"><div class="label">Files Touched</div><div class="value green">${new Set(data.map(f=>f.path)).size}</div></div>
        <div class="stat-card"><div class="label">Reads</div><div class="value">${data.filter(f=>f.op==='read').length}</div></div>
        <div class="stat-card"><div class="label">Writes+Edits</div><div class="value yellow">${data.filter(f=>f.op==='write'||f.op==='edit').length}</div></div>
      </div>
      <div class="panel"><div class="panel-body">
        <table><tr><th>Path</th><th>Op</th><th>Project</th><th>Type</th><th>Time</th></tr>
          ${data.map(f=>`
            <tr>
              <td class="text-monospace">${f.path||'-'}</td>
              <td><span class="tag tag-file">${f.op}</span></td>
              <td>${f.project||'-'}</td>
              <td>${f.file_type||'-'}</td>
              <td class="text-sm text-muted">${(f.ts||'').slice(0,16)}</td>
            </tr>`).join('')}
        </table>
      </div></div>
    </div>`;
}

async function loadKnowledge() {
  const data = await fetchJSON(`${API}/knowledge`);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Knowledge Cards</div>
      <div class="page-subtitle">LLM-generated insights and patterns</div>
      ${data.length===0?'<div class="panel"><div class="panel-body" style="padding:24px;text-align:center;color:var(--text-muted)">No knowledge cards yet. Run Knowledge Skill to generate insights.</div></div>':''}
      ${data.map(k=>`
        <div class="panel">
          <div class="panel-header"><span class="tag tag-${k.type||'best'}">${k.type||'unknown'}</span> ${k.title} <span class="count">${(k.generated_at||'').slice(0,10)}</span></div>
          <div class="panel-body" style="padding:16px">
            <div class="text-sm" style="margin-bottom:12px">${k.summary||''}</div>
            <div class="flex gap-sm"><span class="text-xs text-muted">Session:</span><span class="text-xs text-monospace">${(k.session_id||'').slice(0,20)}</span></div>
            <div class="flex gap-sm mt-sm"><span class="text-xs text-muted">Project:</span><span>${k.project||'-'}</span><span class="text-xs text-muted">Skills:</span><span>${k.skills||'[]'}</span></div>
          </div>
        </div>`).join('')}
    </div>`;
}

async function loadInitiatives() {
  const data = await fetchJSON(`${API}/initiatives`);
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="page-title">Initiatives</div>
      <div class="page-subtitle">Cross-session workstreams</div>
      ${data.length===0?'<div class="panel"><div class="panel-body" style="padding:24px;text-align:center;color:var(--text-muted)">No initiatives tracked.</div></div>':`
      <div class="panel"><div class="panel-body">
        <table><tr><th>Initiative</th><th>Project</th><th>Sessions</th><th>Tool Calls</th></tr>
          ${data.map(i=>`
            <tr>
              <td><span class="tag tag-session">${i.initiative}</span></td>
              <td>${i.project||'-'}</td>
              <td>${i.session_count}</td>
              <td>${i.tool_count}</td>
            </tr>`).join('')}
        </table>
      </div></div>`}
    </div>`;
}

async function viewSession(id) {
  const data = await fetchJSON(`${API}/sessions/${id}`);
  const s = data.session;
  const summary = data.summary;
  document.getElementById('main').innerHTML = `
    <div class="content">
      <div class="flex flex-between mb-lg">
        <div>
          <div class="page-title">${(s.id||'').slice(0,24)}...</div>
          <div class="page-subtitle">
            <span class="tag tag-tool">${s.ide||'?'}</span>
            ${s.project?`<span class="tag tag-file">${s.project}</span>`:''}
            ${s.branch?`<span class="tag tag-session">${s.branch}</span>`:''}
            ${s.initiative?`<span class="tag tag-knowledge">${s.initiative}</span>`:''}
          </div>
        </div>
        <span class="clickable" onclick="navigate('sessions')">← Back</span>
      </div>
      <div class="grid-3 mb-lg">
        <div class="stat-card"><div class="label">Messages</div><div class="value">${data.messages.length}</div></div>
        <div class="stat-card"><div class="label">Tool Calls</div><div class="value blue">${data.tool_calls.length}</div></div>
        <div class="stat-card"><div class="label">Files Touched</div><div class="value green">${data.file_ops.length}</div></div>
        ${data.stats?`
          <div class="stat-card"><div class="label">Skills Used</div><div class="value red">${data.stats.skill_count||0}</div></div>
          <div class="stat-card"><div class="label">Bash Commands</div><div class="value yellow">${data.stats.bash_count||0}</div></div>
          <div class="stat-card"><div class="label">Duration</div><div class="value">${data.stats.duration_min||'?'}m</div></div>
        `:''}
      </div>
      ${summary?`
      <div class="panel mb-lg"><div class="panel-header">AI Summary</div>
        <div class="panel-body" style="padding:16px">
          <div class="grid-2">
            <div class="summary-card"><div class="label">Context to Remember</div><div class="text">${summary.context_to_remember||'-'}</div></div>
            <div class="summary-card"><div class="label">Efficiency Score</div><div class="text" style="font-size:20px;font-weight:700;color:${(summary.efficiency_score||0)>0.6?'var(--green)':'var(--yellow)'}">${summary.efficiency_score?Math.round(summary.efficiency_score*100)+'%':'-'}</div></div>
            <div class="summary-card"><div class="label">Efficiency Tip</div><div class="text">${summary.efficiency_tip||'-'}</div></div>
            <div class="summary-card"><div class="label">Memory Keywords</div><div class="text">${summary.memory_keywords||'-'}</div></div>
          </div>
        </div>
      </div>`:''}
      <div class="panel mb-lg"><div class="panel-header">Messages<span class="count">${data.messages.length}</span></div>
        <div class="panel-body" style="max-height:400px;overflow-y:auto">
          ${data.messages.map(m=>`
            <div style="padding:6px 16px;border-bottom:1px solid var(--border);font-size:12px">
              <span class="tag ${m.type==='user'?'tag-skill':'tag-tool'}" style="margin-right:8px">${m.type}</span>
              ${(m.content||'').slice(0,500)}
            </div>`).join('')}
        </div>
      </div>
      <div class="panel"><div class="panel-header">Tool Calls<span class="count">${data.tool_calls.length}</span></div>
        <div class="panel-body" style="max-height:500px;overflow-y:auto">
          <table><tr><th>Tool</th><th>Call ID</th><th>Args</th><th>Duration</th></tr>
            ${data.tool_calls.map(t=>`
              <tr>
                <td><span class="tag tag-tool">${t.tool}</span></td>
                <td class="text-xs text-monospace">${(t.call_id||'').slice(0,16)}</td>
                <td class="text-xs" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(t.args||'').slice(0,80)}</td>
                <td>${t.duration_ms?t.duration_ms+'ms':'-'}</td>
              </tr>`).join('')}
          </table>
        </div>
      </div>
    </div>`;
}

renderSidebar();
loadOverview();
