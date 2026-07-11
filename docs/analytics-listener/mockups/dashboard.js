
var D={projects:[
{id:"ai-coworker",name:"ai-coworker",sessions:8,files:34,skills:12,knowledge:14,active:true,depends_on:[],depended_by:["skill-factory"],created:"2025-03-15",last_session:"2026-06-11 14:32"},
{id:"skill-factory",name:"skill-factory",sessions:2,files:6,skills:2,knowledge:4,active:false,depends_on:["ai-coworker"],depended_by:[],created:"2026-05-10",last_session:"2026-06-09"},
{id:"dotfiles",name:"~/.claude",sessions:1,files:4,skills:0,knowledge:2,active:false,depends_on:[],depended_by:[],created:"2025-01-01",last_session:"2026-06-01"},
{id:"new-project",name:"new-project",sessions:0,files:0,skills:0,knowledge:0,active:false,depends_on:[],depended_by:[],created:"2026-06-10",last_session:null}],
sessions:[
{id:"s1",project:"ai-coworker",branch:"feat/dashboard",initiative:"dashboard-v1",started:"2026-06-11 14:20",ended:null,status:"active",
workflow:[{phase:"Explore",icon:"🔍",desc:"Analyzed ai-coworker codebase structure"},{phase:"Brainstorm",icon:"🧠",desc:"Designed 12 dashboard views with visual companion"},{phase:"Review",icon:"🔎",desc:"Feasibility review: deleted 3 views, simplified 3, kept 5 MVP"},{phase:"Design",icon:"🎨",desc:"Built v2 object-relationship model with 7 entity types"},{phase:"Docs",icon:"📝",desc:"Reorganized to prd/spec/plan/test, wrote 3 PRDs"}],
skills:["brainstorming","writing-plans"],tools:["read","write","edit","bash","task"],files_r:["CLAUDE.md","src/coworker/models.py"],files_w:["src/coworker/dashboard.py","docs/prd/PRD.md"],knowledge:["k1","k3"]},
{id:"s2",project:"ai-coworker",branch:"feat/dashboard",initiative:"dashboard-v1",started:"2026-06-10 15:20",ended:"2026-06-10 15:42",status:"done",
workflow:[{phase:"Explore",icon:"🔍",desc:"Read coworker-blueprint.md and existing docs"},{phase:"Brainstorm",icon:"🧠",desc:"Defined 3-layer architecture"},{phase:"Design",icon:"🎨",desc:"Created DESIGN.md and plan-dashboard.yaml"}],
skills:["brainstorming","writing-plans"],tools:["read","write"],files_r:["coworker-blueprint.md","src/coworker/models.py"],files_w:["docs/design/DESIGN.md","docs/planning/plan-dashboard.yaml"],knowledge:["k2"]},
{id:"s3",project:"ai-coworker",branch:"fix/config",initiative:null,started:"2026-06-09 10:00",ended:"2026-06-09 10:20",status:"done",
workflow:[{phase:"Debug",icon:"🐛",desc:"Used systematic-debugging to trace config sync failure"},{phase:"Fix",icon:"🔧",desc:"Fixed config.py typo, ran pytest to verify"}],
skills:["systematic-debugging"],tools:["read","edit","bash"],files_r:["src/coworker/config.py","global/coworker.yaml"],files_w:["src/coworker/config.py"],knowledge:["k4"]}],
skills:[
{id:"brainstorming",calls:14,called_by:["writing-plans","executing-plans"],sessions:["s1","s2"],tools:["read","write","question"],last_invoked:"2026-06-11 14:21",content:"SKILL: brainstorming\nUse before any creative work.\nProcess: Explore context, Ask questions, Propose approaches, Present design, Write doc."},
{id:"writing-plans",calls:12,called_by:[],sessions:["s1","s2"],tools:["write"],last_invoked:"2026-06-11 14:25",content:"SKILL: writing-plans\nUse when you have specs for multi-step tasks.\nOutput: Implementation plan with waves and MAC."},
{id:"systematic-debugging",calls:7,called_by:[],sessions:["s3"],tools:["read","bash","edit"],last_invoked:"2026-06-09 10:02",content:"SKILL: systematic-debugging\nUse when encountering bugs or test failures.\nProcess: Reproduce, Isolate, Propose fix, Verify."},
{id:"executing-plans",calls:8,called_by:[],sessions:[],tools:["task","bash"],last_invoked:"2026-06-08 16:30",content:""},
{id:"subagent-driven-dev",calls:5,called_by:[],sessions:[],tools:["task"],last_invoked:"2026-06-07 11:15",content:""}],
tools:[
{id:"read",type:"builtin",calls:89,avg:"0.2s",max:"0.8s",sessions:["s1","s2","s3"]},
{id:"write",type:"builtin",calls:34,avg:"0.3s",max:"1.2s",sessions:["s1","s2"]},
{id:"edit",type:"builtin",calls:28,avg:"1.1s",max:"5.3s",sessions:["s1","s3"]},
{id:"bash",type:"builtin",calls:45,avg:"2.3s",max:"45s",sessions:["s1","s3"]},
{id:"task",type:"builtin",calls:12,avg:"18.7s",max:"62s",sessions:["s1"]},
{id:"question",type:"builtin",calls:8,avg:"0s",max:"45s",sessions:["s1"]},
{id:"github",type:"mcp",calls:6,avg:"1.2s",max:"3.5s",sessions:["s1"],server:"github-mcp"},
{id:"slack",type:"mcp",calls:3,avg:"0.8s",max:"2.1s",sessions:["s2"],server:"slack-mcp"}],
files:[
{id:"CLAUDE.md",path:"CLAUDE.md",project:"ai-coworker",sessions:["s1","s2"],read_by_skill:["brainstorming"],read_by_tool:["read"],written_by_tool:["edit"],last_read:"2026-06-11 14:22",last_written:"2026-06-11 14:30",created:"2025-03-15"},
{id:"src/coworker/models.py",path:"src/coworker/models.py",project:"ai-coworker",sessions:["s1","s2"],read_by_skill:["brainstorming","writing-plans"],read_by_tool:["read"],written_by_tool:["edit"],last_read:"2026-06-11 14:22",last_written:"2026-06-10 15:35",created:"2025-03-15"},
{id:"src/coworker/dashboard.py",path:"src/coworker/dashboard.py",project:"ai-coworker",sessions:["s1"],read_by_skill:[],read_by_tool:[],written_by_tool:["write"],last_read:null,last_written:"2026-06-11 14:28",created:"2026-06-11"},
{id:"src/coworker/config.py",path:"src/coworker/config.py",project:"ai-coworker",sessions:["s3"],read_by_skill:["systematic-debugging"],read_by_tool:["read"],written_by_tool:["edit"],last_read:"2026-06-09 10:02",last_written:"2026-06-09 10:15",created:"2025-03-15"},
{id:"global/coworker.yaml",path:"global/coworker.yaml",project:"ai-coworker",sessions:["s3"],read_by_skill:["systematic-debugging"],read_by_tool:["read"],written_by_tool:[],last_read:"2026-06-09 10:02",last_written:null,created:"2025-03-15"}],
knowledge:[
{id:"k1",title:"pytest fails in worktree",type:"trap",session:"s1",project:"ai-coworker",skills:["systematic-debugging"],text:"pytest not found in worktree — use python3 -m pytest",evidence:['bash "pytest" returned command not found','bash "python3 -m pytest" succeeded','Worktree venv path resolution issue'],generated:"2026-06-11 14:40"},
{id:"k2",title:"brainstorm before coding",type:"best",session:"s2",project:"ai-coworker",skills:["brainstorming"],text:"Always run brainstorming before new features. Design doc rate 60% to 95%.",evidence:['brainstorming produced DESIGN.md','Without brainstorming: 2 major reworks','Global: 12 with brainstorming avg 1.2 reworks'],generated:"2026-06-10 16:00"},
{id:"k3",title:"edit unstable >500 lines",type:"trap",session:"s1",project:"ai-coworker",skills:["brainstorming"],text:"edit fails on files >500 lines. Use write instead.",evidence:['edit on cli.py (744 lines) failed 3x','write succeeded first attempt','Self-healing rule #7 generated'],generated:"2026-06-11 14:42"},
{id:"k4",title:"--workdir more reliable",type:"pattern",session:"s3",project:"ai-coworker",skills:["systematic-debugging"],text:"OpenCode --workdir is more reliable than cd.",evidence:['cd && pytest failed in worktree','opencode --workdir resolved path'],generated:"2026-06-09 10:30"}],
initiatives:[{id:"dashboard-v1",project:"ai-coworker",sessions:["s1","s2"],skills:["brainstorming","writing-plans"],files:["CLAUDE.md","models.py","dashboard.py"],knowledge:["k1","k2","k3"]}]};
var L=function(arr,id){for(var i=0;i<arr.length;i++){if(arr[i].id===id)return arr[i]}return null};
var bp=function(arr,pid){return arr.filter(function(x){return x.project===pid})};

function navigate(view){
  var items=document.querySelectorAll(".sitem");
  for(var i=0;i<items.length;i++)items[i].classList.remove("active");
  var idx={projects:0,sessions:1,skills:2,tools:3,files:4,knowledge:5,initiatives:6}[view];
  items[idx].classList.add("active");
  var fns={projects:renderProjects,sessions:renderAllSessions,skills:renderSkills,tools:renderTools,files:renderFilesView,knowledge:renderKnowledgeView,initiatives:renderInitiatives};
  document.getElementById("content").innerHTML=fns[view]();
}

function toggle(id){
  var el=document.getElementById("expand-"+id);
  if(el)el.classList.toggle("open");
}

function tab(e,name,pid){
  e.stopPropagation();
  var p=document.getElementById("expand-"+pid);
  var tbs=p.querySelectorAll(".tbtn");
  for(var i=0;i<tbs.length;i++)tbs[i].classList.remove("active");
  var tcs=p.querySelectorAll(".tc");
  for(var i=0;i<tcs.length;i++)tcs[i].classList.remove("active");
  e.currentTarget.classList.add("active");
  document.getElementById("tab-"+name+"-"+pid).classList.add("active");
}

function esc(s){return s.replace(/'/g,"\\'")}

function renderProjects(){
  var h="<h2>Projects</h2><p class='sub'>Click to explore sessions, files, skills, and knowledge per project</p>";
  D.projects.forEach(function(p){
    var icon=p.active?"🟢":"⚫";
    h+="<div class='list-item' onclick=\"toggle('project-"+p.id+"')\">";
    h+="<span class='lname'>"+icon+" "+p.name+"</span>";
    h+="<span class='lmeta'>"+p.sessions+" sessions</span>";
    h+="<span class='lmeta'>"+p.files+" files</span>";
    h+="<span class='lmeta'>"+p.knowledge+" knowledge</span>";
    h+="<span class='lmeta dim'>created "+p.created+"</span>";
    h+="<span class='lmeta dim'>last "+(p.last_session||"never")+"</span>";
    if(p.depends_on.length)h+="<span class='badge bg-wait'>depends: "+p.depends_on.join(",")+"</span>";
    if(p.depended_by.length)h+="<span class='badge bg-done'>used by: "+p.depended_by.join(",")+"</span>";
    h+="</div>";
    
    h+="<div class='lexpand' id='expand-project-"+p.id+"'>";
    h+="<div class='tab-bar'>";
    h+="<div class='tbtn active' onclick=\"tab(event,'sessions','project-"+p.id+"')\">Sessions</div>";
    h+="<div class='tbtn' onclick=\"tab(event,'files','project-"+p.id+"')\">Files</div>";
    h+="<div class='tbtn' onclick=\"tab(event,'knowledge','project-"+p.id+"')\">Knowledge</div>";
    h+="<div class='tbtn' onclick=\"tab(event,'knowledge','project-"+p.id+"')\">Knowledge</div>";
    h+="</div>";
    h+="<div class='tc active' id='tab-sessions-project-"+p.id+"'>"+renderSessions(bp(D.sessions,p.id))+"</div>";
    h+="<div class='tc' id='tab-files-project-"+p.id+"'>"+renderFiles(bp(D.files,p.id))+"</div>";
    h+="<div class='tc' id='tab-knowledge-project-"+p.id+"'>"+renderKnowledge(D.knowledge.filter(function(k){return k.project===p.id}))+"</div>";
    h+="</div>";
  });
  h+="<div class='graph-box' style='margin-top:16px;min-height:80px'><div style='text-align:center;font-size:10px;color:#8b949e'>";
  h+="<b>Project Relationships</b><br><br>";
  var hasAny=D.projects.some(function(p){return p.depends_on.length||p.depended_by.length});
  if(hasAny){
    D.projects.forEach(function(p){
      if(p.depends_on.length){h+="<span class='gnode gp'>"+p.name+"</span> <span style='color:#d29922'>→</span> "+p.depends_on.map(function(d){return"<span class='gnode gp'>"+d+"</span>"}).join(" ")+" &nbsp;&nbsp; "}
      if(p.depended_by.length){h+="<span class='gnode gp'>"+p.name+"</span> <span style='color:#58a6ff'>←</span> "+p.depended_by.map(function(d){return"<span class='gnode gp'>"+d+"</span>"}).join(" ")+" &nbsp;&nbsp; "}
    });
  }else{h+="No project dependencies"}
  h+="</div></div>";
  return h;
}

function renderSessions(ss){
  if(!ss.length)return"<div class='dim p11'>No sessions</div>";
  return ss.map(function(s){return renderSessionCard(s)}).join("");
}

function renderAllSessions(){
  return"<h2>All Sessions</h2><p class='sub'>Click to see how each task was completed</p>"+D.sessions.map(function(s){return renderSessionCard(s)}).join("");
}

function renderSessionCard(s){
  var dur=s.ended?Math.round((new Date(s.ended)-new Date(s.started))/60000)+"min":"in progress";
  var icon=s.status==="active"?"🟢":"✅";
  var h="<div class='list-item' onclick=\"toggle('session-"+s.id+"')\">";
  h+="<span class='lname'>"+icon+" "+s.branch+"</span>";
  h+="<span class='lmeta'>"+s.started+"</span>";
  h+="<span class='lmeta'>"+dur+"</span>";
  h+="<span class='lmeta'>"+s.skills.length+" skills</span>";
  h+="<span class='lmeta'>"+s.tools.length+" tools</span>";
  if(s.initiative)h+="<span class='badge bg-active'>"+s.initiative+"</span>";
  h+="</div>";
  
  h+="<div class='lexpand' id='expand-session-"+s.id+"'>";
  h+="<div class='grid2 mb8'>";
  h+="<div class='card'><div class='ctitle'>Timing</div><div class='p10'><b>Started:</b> "+s.started+"<br><b>Ended:</b> "+(s.ended||"ongoing")+"<br><b>Duration:</b> "+dur+"</div></div>";
  h+="<div class='card'><div class='ctitle'>Context</div><div class='p10'><b>Project:</b> "+L(D.projects,s.project).name+"<br><b>Branch:</b> "+s.branch+"<br><b>Initiative:</b> "+(s.initiative||"none")+"</div></div>";
  h+="</div>";
  h+="<div class='card mb8'><div class='ctitle'>How It Was Done</div>";
  s.workflow.forEach(function(w,i){
    h+="<div class='workflow-step'><div class='wf-icon'>"+w.icon+"</div><div><b>"+w.phase+":</b> "+w.desc+"</div></div>";
    if(i<s.workflow.length-1)h+="<div class='wf-conn'>|</div>";
  });
  h+="</div>";
  h+="<div class='grid2 mb8'>";
  h+="<div class='card'><div class='ctitle'>Skills Used</div>"+s.skills.map(function(sk){return"<span class='tag tag-s'>"+sk+"</span>"}).join(" ")+"</div>";
  h+="<div class='card'><div class='ctitle'>Tools</div>"+s.tools.map(function(t){return"<span class='tag tag-t'>"+t+"</span>"}).join(" ")+"</div>";
  h+="<div class='card'><div class='ctitle'>Files Read</div>"+s.files_r.map(function(f){return"<span class='tag tag-f'>"+f+"</span>"}).join(" ")+"</div>";
  h+="<div class='card'><div class='ctitle'>Files Written</div>"+s.files_w.map(function(f){return"<span class='tag tag-f'>"+f+"</span>"}).join(" ")+"</div>";
  h+="</div>";
  h+="<div class='card'><div class='ctitle'>Related Knowledge</div>";
  if(s.knowledge.length){
    s.knowledge.forEach(function(kid){var k=L(D.knowledge,kid);if(k)h+="<span class='tag tag-k'>"+k.type+": "+k.title+"</span>"});
  }else{h+="<span class='dim p10'>No knowledge cards yet</span>"}
  h+="</div></div>";
  return h;
}

function renderSkills(){
  var h="<h2>Skills</h2><p class='sub'>Click to see callers, dependencies, sessions — expand to view skill content</p>";
  D.skills.forEach(function(sk){
    h+="<div class='list-item' onclick=\"toggle('skill-"+sk.id+"')\">";
    h+="<span class='lname'>🧠 "+sk.id+"</span>";
    h+="<span class='lmeta'>"+sk.calls+" calls</span>";
    h+="<span class='lmeta'>"+sk.sessions.length+" sessions</span>";
    h+="<span class='lmeta dim'>last: "+sk.last_invoked+"</span>";
    if(sk.called_by.length)h+="<span class='badge bg-active'>called by: "+sk.called_by.join(",")+"</span>";
    else h+="<span class='badge bg-done'>top-level</span>";
    if(sk.content)h+="<span class='btn btn-outline' style='margin-left:8px;font-size:9px' onclick=\"event.stopPropagation();viewSkill('"+sk.id+"')\">View</span>";
    h+="</div>";
    
    h+="<div class='lexpand' id='expand-skill-"+sk.id+"'>";
    h+="<div class='grid2 mb8'>";
    h+="<div class='card'><div class='ctitle'>Invocation Count</div><div class='p13 good'>"+sk.calls+"</div></div>";
    h+="<div class='card'><div class='ctitle'>Last Invoked</div><div class='p10'>"+sk.last_invoked+"</div></div>";
    h+="<div class='card'><div class='ctitle'>Called by Skills</div>";
    if(sk.called_by.length)sk.called_by.forEach(function(s){h+="<span class='tag tag-s'>"+s+"</span>"});
    else h+="<span class='dim p10'>top-level skill</span>";
    h+="</div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>";
    if(sk.sessions.length)sk.sessions.forEach(function(sid){h+="<span class='tag tag-se'>"+L(D.sessions,sid).branch+"</span>"});
    else h+="<span class='dim p10'>none</span>";
    h+="</div>";
    h+="<div class='card'><div class='ctitle'>Tools Used</div>"+sk.tools.map(function(t){return"<span class='tag tag-t'>"+t+"</span>"}).join(" ")+"</div>";
    h+="</div>";
    if(sk.content)h+="<div class='card'><div class='ctitle'>Skill Content (SKILL.md)</div><div class='skill-content'>"+sk.content+"</div></div>";
    h+="</div>";
    
    h+="<div class='lexpand' id='skill-view-"+sk.id+"'>";
    h+="<div class='card'><div class='ctitle'>"+sk.id+" — Full Skill Content</div><div class='skill-content'>"+(sk.content||"(No content)")+"</div></div>";
    h+="<div class='btn btn-outline' style='margin-top:8px' onclick=\"toggle('skill-view-"+sk.id+"')\">Close</div>";
    h+="</div>";
  });
  return h;
}

function viewSkill(id){
  var els=document.querySelectorAll(".lexpand");
  for(var i=0;i<els.length;i++)els[i].classList.remove("open");
  var el=document.getElementById("skill-view-"+id);
  if(el)el.classList.add("open");
}

function renderTools(){
  var h="<h2>Tools</h2><p class='sub'>Builtin + MCP tools — click to see usage across sessions</p>";
  
  h+="<div class='card mb12'><div class='ctitle'>MCP Tools <span class='badge bg-future'>via MCP servers</span></div>";
  var mcps=D.tools.filter(function(t){return t.type==="mcp"});
  if(!mcps.length)h+="<div class='dim p10'>No MCP tools</div>";
  mcps.forEach(function(t){
    h+="<div class='list-item' onclick=\"toggle('tool-"+t.id+"')\">";
    h+="<span class='lname'>"+t.id+" <span class='tag tag-mcp'>MCP</span></span>";
    h+="<span class='lmeta'>"+t.server+"</span><span class='lmeta'>"+t.calls+" calls</span><span class='lmeta'>avg "+t.avg+"</span>";
    h+="</div><div class='lexpand' id='expand-tool-"+t.id+"'>";
    h+="<div class='grid2'><div class='card'><div class='ctitle'>MCP Server</div><div class='p10'>"+t.server+"</div></div>";
    h+="<div class='card'><div class='ctitle'>Performance</div><div class='p10'>avg: <span class='good'>"+t.avg+"</span> | max: <span class='warn'>"+t.max+"</span></div></div></div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>"+t.sessions.map(function(sid){return"<span class='tag tag-se'>"+L(D.sessions,sid).branch+"</span>"}).join(" ")+"</div>";
    h+="</div>";
  });
  h+="</div>";
  
  h+="<div class='card'><div class='ctitle'>Builtin Tools</div>";
  D.tools.filter(function(t){return t.type==="builtin"}).forEach(function(t){
    h+="<div class='list-item' onclick=\"toggle('tool-"+t.id+"')\">";
    h+="<span class='lname'>"+t.id+"</span>";
    h+="<span class='lmeta'>"+t.calls+" calls</span><span class='lmeta'>avg "+t.avg+"</span><span class='lmeta'>max "+t.max+"</span>";
    h+="</div><div class='lexpand' id='expand-tool-"+t.id+"'>";
    h+="<div class='grid2'><div class='card'><div class='ctitle'>Total Calls</div><div class='p13 info'>"+t.calls+"</div></div>";
    h+="<div class='card'><div class='ctitle'>Performance</div><div class='p10'>avg: <span class='good'>"+t.avg+"</span> | max: <span class='warn'>"+t.max+"</span></div></div></div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>"+t.sessions.map(function(sid){return"<span class='tag tag-se'>"+L(D.sessions,sid).branch+"</span>"}).join(" ")+"</div>";
    h+="</div>";
  });
  h+="</div>";
  return h;
}

function renderFilesView(){
  var h="<h2>Files</h2><p class='sub'>All files with project, session, skill/tool relationships</p>";
  D.files.forEach(function(f){
    h+="<div class='list-item' onclick=\"toggle('file-"+f.id+"')\">";
    h+="<span class='lname'>"+f.id+"</span>";
    h+="<span class='lmeta'>"+L(D.projects,f.project).name+"</span>";
    h+="<span class='lmeta'>"+f.sessions.length+" sessions</span>";
    h+="<span class='lmeta dim'>read: "+(f.last_read||"never")+"</span>";
    h+="<span class='lmeta dim'>write: "+(f.last_written||"never")+"</span>";
    h+="</div><div class='lexpand' id='expand-file-"+f.id+"'>";
    h+="<div class='grid2'>";
    h+="<div class='card'><div class='ctitle'>Project</div><span class='tag tag-se'>"+L(D.projects,f.project).name+"</span></div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>"+f.sessions.map(function(sid){return"<span class='tag tag-se'>"+L(D.sessions,sid).branch+"</span>"}).join(" ")+"</div>";
    h+="<div class='card'><div class='ctitle'>Read by Skills</div>"+(f.read_by_skill.length?f.read_by_skill.map(function(sk){return"<span class='tag tag-s'>"+sk+"</span>"}).join(" "):"<span class='dim p10'>none</span>")+"</div>";
    h+="<div class='card'><div class='ctitle'>Read/Write by Tools</div>"+f.read_by_tool.map(function(t){return"<span class='tag tag-t'>read:"+t+"</span>"}).join(" ")+" "+f.written_by_tool.map(function(t){return"<span class='tag tag-t'>write:"+t+"</span>"}).join(" ")+"</div>";
    h+="</div></div>";
  });
  return h;
}

function renderFiles(files){
  if(!files.length)return"<div class='dim p11'>No files</div>";
  return files.map(function(f){
    var h="<div class='list-item' onclick=\"toggle('file-"+f.id+"')\" style='margin-left:16px'>";
    h+="<span class='lname'>"+f.id+"</span><span class='lmeta'>"+f.sessions.length+" sessions</span>";
    h+="<span class='lmeta dim'>read: "+(f.last_read||"never")+"</span><span class='lmeta dim'>write: "+(f.last_written||"never")+"</span>";
    h+="</div><div class='lexpand' id='expand-file-"+f.id+"'>";
    h+="<div class='grid2'><div class='card'><div class='ctitle'>Project</div><span class='tag tag-se'>"+L(D.projects,f.project).name+"</span></div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>"+f.sessions.map(function(sid){return"<span class='tag tag-se'>"+L(D.sessions,sid).branch+"</span>"}).join(" ")+"</div></div></div>";
    return h;
  }).join("");
}

function renderKnowledgeView(){
  var h="<h2>Knowledge Cards</h2><p class='sub'>Generated by Knowledge Skill — click to see evidence, source, and create skill</p>";
  D.knowledge.forEach(function(k){h+=renderKnowledgeCard(k)});
  return h;
}

function renderKnowledge(klist){
  if(!klist.length)return"<div class='dim p11'>No knowledge cards — run Knowledge Skill</div>";
  return klist.map(function(k){return renderKnowledgeCard(k)}).join("");
}

function renderKnowledgeCard(k){
  var s=L(D.sessions,k.session),p=L(D.projects,k.project);
  var icons={trap:"⚠️",best:"✅",pattern:"📋"};
  var h="<div class='list-item' onclick=\"toggle('knowledge-"+k.id+"')\">";
  h+="<span class='lname'>"+(icons[k.type]||"📝")+" "+k.title+"</span>";
  h+="<span class='lmeta'>"+k.generated+"</span>";
  h+="<span class='lmeta'>"+(s?s.branch:"?")+"</span>";
  h+="<span class='lmeta'>"+(p?p.name:"?")+"</span>";
  if(k.skills.length)h+="<span class='lmeta'>"+k.skills.length+" skills</span>";
  h+="</div>";
  
  h+="<div class='lexpand' id='expand-knowledge-"+k.id+"'>";
  h+="<div class='p10 mb8' style='color:#c9d1d9'>"+k.text+"</div>";
  h+="<div class='grid2 mb8'>";
  h+="<div class='card'><div class='ctitle'>Source Session</div><div class='p10'><b>Branch:</b> "+(s?s.branch:k.session)+"<br><b>Project:</b> "+(p?p.name:k.project)+"<br><b>Time:</b> "+(s?s.started:"?")+"</div></div>";
  h+="<div class='card'><div class='ctitle'>Related Skills</div>"+k.skills.map(function(sk){return"<span class='tag tag-s'>"+sk+"</span>"}).join(" ")+"</div>";
  h+="</div>";
  h+="<div class='card mb8'><div class='ctitle'>Evidence</div>";
  k.evidence.forEach(function(e){h+="<div class='evidence-item'>"+e+"</div>"});
  h+="</div>";
  h+="<div style='display:flex;gap:8px'>";
  h+="<div class='btn btn-primary' onclick=\"alert('Creating skill from: "+esc(k.title)+"\\n\\nWould call opencode SDK:\\nconst { client } = await createOpencode();\\nawait client.session.prompt({...});')\">Create Skill from this Card</div>";
  h+="<div class='btn btn-outline'>Refine with AI</div>";
  h+="</div>";
  h+="<div class='p10 dim mt4'>Creating a skill calls opencode/claude SDK (ensured by coworker install) to scaffold SKILL.md from evidence and patterns.</div>";
  h+="</div>";
  return h;
}

function renderInitiatives(){
  var h="<h2>Initiatives</h2><p class='sub'>Cross-session workstreams — click to see linked sessions, skills, files, and knowledge</p>";
  D.initiatives.forEach(function(init){
    h+="<div class='list-item' onclick=\"toggle('initiative-"+init.id+"')\">";
    h+="<span class='lname'>🎯 "+init.id+"</span>";
    h+="<span class='lmeta'>"+init.sessions.length+" sessions</span>";
    h+="<span class='lmeta'>"+init.skills.length+" skills</span>";
    h+="<span class='lmeta'>"+init.files.length+" files</span>";
    h+="<span class='lmeta'>"+init.knowledge.length+" knowledge</span>";
    var p=L(D.projects,init.project);
    h+="<span class='lmeta dim'>project: "+(p?p.name:"?")+"</span>";
    h+="</div>";
    h+="<div class='lexpand' id='expand-initiative-"+init.id+"'>";
    h+="<div class='grid2 mb8'>";
    h+="<div class='card'><div class='ctitle'>Project</div><span class='tag tag-se'>"+(p?p.name:init.project)+"</span></div>";
    h+="<div class='card'><div class='ctitle'>Sessions</div>"+init.sessions.map(function(sid){var s=L(D.sessions,sid);return s?"<span class='tag tag-se'>"+s.branch+"</span>":sid}).join(" ")+"</div>";
    h+="</div>";
    h+="<div class='grid2 mb8'>";
    h+="<div class='card'><div class='ctitle'>Skills</div>"+init.skills.map(function(sk){return"<span class='tag tag-s'>"+sk+"</span>"}).join(" ")+"</div>";
    h+="<div class='card'><div class='ctitle'>Files</div>"+init.files.map(function(f){return"<span class='tag tag-f'>"+f+"</span>"}).join(" ")+"</div>";
    h+="</div>";
    h+="<div class='card'><div class='ctitle'>Knowledge Cards</div>"+init.knowledge.map(function(kid){var k=L(D.knowledge,kid);return k?"<span class='tag tag-k'>"+k.type+": "+k.title+"</span>":""}).join(" ")+"</div>";
    h+="<div class='graph-box' style='margin-top:12px;min-height:60px'><div style='text-align:center;font-size:10px;color:#8b949e'><b>Context Assembly <span class='bg-future'>FUTURE</span></b><br>Drag skills, files, and knowledge cards here to build initiative context that auto-injects into CLAUDE.md</div></div>";
    h+="</div>";
  });
  return h;
}

navigate("projects");
