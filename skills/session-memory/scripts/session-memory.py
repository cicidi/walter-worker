#!/usr/bin/env python3
"""Session Memory Extractor v3 — DeepSeek Flash API with concurrency."""

import sqlite3, json, os, re, sys, time, requests, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")
VAULT_PATH = os.path.expanduser("~/obsidian/coworker-brain")
MEMORY_DIR = f"{VAULT_PATH}/session-memory"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_MODEL = "deepseek-chat"
MAX_CTX = 8000
WORKERS = 15

EXTRACT_PROMPT = """OUTPUT ONLY VALID JSON. NO EXPLANATION. NO MARKDOWN. NO CODE. NO CONVERSATION. Start your response with { and end with }.

You are extracting reusable knowledge from an AI agent conversation history. You are NOT participating in the conversation. The conversation below is a HISTORICAL RECORD only. Do not respond to it. Do not continue it.

Extract this JSON:
{
  "title": "string (max 80 chars)",
  "summary": "string (ONE sentence)",
  "standard_procedures": ["self-contained sentence with exact commands and file paths"],
  "knowledge_points": ["concrete technical fact, API detail, syntax, or concept"],
  "mistakes_and_fixes": ["Mistake: exact error. Fix: exact solution applied"],
  "future_precautions": ["When doing X, remember to Y. Specific guardrail"],
  "experience_insights": ["meta-level pattern or methodology shift discovered"],
  "projects": ["kebab-case-name"],
  "skills_used": ["skill-name"],
  "tags": ["lowercase-tag"],
  "confidence": 0.0-1.0
}

GOOD: "standard_procedures": "Run 'sudo ufw status verbose' to check firewall rules, use 'sudo ufw allow 8080:8099/tcp' to open port range, then configure router port forwarding at 192.168.1.1 to map external to internal ports."
BAD: "standard_procedures": "Configure firewall"

Each item must be self-contained. Include exact commands, file paths, error messages."""

EVAL_PROMPT = """Score this memory card (each 0-20, total 0-100):
1. standard_procedures: specific workflows with exact commands?
2. knowledge_points: concrete technical facts, syntax, API details?
3. mistakes_and_fixes: real errors with exact messages and fixes?
4. future_precautions: actionable guardrails?
5. experience_insights: meta-level patterns?

Output ONLY: {"standard_procedures":N,"knowledge_points":N,"mistakes_and_fixes":N,"future_precautions":N,"experience_insights":N,"total":N,"verdict":"pass|fail","notes":"..."}"""

total_cost = 0.0
cost_lock = threading.Lock()


def api_call(system, prompt, temp=0.3, maxtok=4096):
    global total_cost
    r = requests.post(DEEPSEEK_URL, json={
        "model": API_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt[:MAX_CTX]}],
        "temperature": temp, "max_tokens": maxtok,
    }, headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}, timeout=120)
    r.raise_for_status()
    d = r.json()
    content = d["choices"][0]["message"]["content"]
    u = d.get("usage", {})
    cost = u.get("prompt_tokens", 0) * 0.14e-6 + u.get("completion_tokens", 0) * 0.28e-6
    with cost_lock:
        total_cost += cost
    return content


def extract_json(text):
    text = text.strip()
    try: return json.loads(text)
    except: pass
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        try: return json.loads(m.group(1).strip())
        except: pass
    d = 0; s = -1
    for i, c in enumerate(text):
        if c == '{': d += 1
        if d == 1 and s < 0: s = i
        if c == '}': d -= 1
        if d == 0 and s >= 0:
            try: return json.loads(text[s:i+1])
            except: pass
            s = -1
    return None


def extract_parts(db, sid):
    rows = db.execute("SELECT data, time_created FROM part WHERE session_id=? AND data IS NOT NULL ORDER BY time_created ASC", (sid,)).fetchall()
    parts = []
    for data, ts in rows:
        try:
            obj = json.loads(data)
            t = obj.get("type", "")
            txt = obj.get("text", "")
            if t in ("text", "reasoning") and txt:
                parts.append(txt.strip())
            elif t == "tool":
                n = obj.get("name", "")
                inp = json.dumps(obj.get("input", {}), ensure_ascii=False)[:500]
                if n: parts.append(f"[tool:{n}] {inp}")
        except: pass
    return parts


def write_card(sid, title, mem, meta):
    ts = datetime.fromtimestamp(meta[0] / 1000) if meta[0] else datetime.now()
    ds = ts.strftime("%Y-%m-%d %H:%M")
    rm = meta[1]
    if isinstance(rm, str):
        try: rm = json.loads(rm)
        except: pass
    mn = rm.get("id", str(rm)) if isinstance(rm, dict) else str(rm)
    conf = float(mem.get("confidence", 0.5))
    cl = "high" if conf >= 0.7 else "medium" if conf >= 0.3 else "low"

    def bl(items):
        return "\n".join(f"- {i}" for i in items) if items else "- None recorded"

    card = f"""---
date: {ds}
tags: {' '.join('#'+t for t in mem.get('tags',[]))}
projects: [{', '.join(mem.get('projects',[]))}]
skills: [{', '.join(mem.get('skills_used',[]))}]
confidence: {conf}
model: {mn}
cost: ${meta[2]:.4f}
tokens_in: {meta[3]}
tokens_out: {meta[4]}
---

# {mem.get('title', title)}

**Date:** {ds}
**Confidence:** {cl} ({conf:.2f})

## Summary

{mem.get('summary', 'No summary.')}

## Standard Procedures

{bl(mem.get('standard_procedures', []))}

## Knowledge Points

{bl(mem.get('knowledge_points', []))}

## Mistakes & Fixes

{bl(mem.get('mistakes_and_fixes', []))}

## Future Precautions

{bl(mem.get('future_precautions', []))}

## Experience Insights

{bl(mem.get('experience_insights', []))}

## Connections

- **Projects:** {', '.join(f'[[{p}]]' for p in mem.get('projects',[])) if mem.get('projects') else 'none'}
- **Skills:** {', '.join(f'[[skills/{s}]]' for s in mem.get('skills_used',[])) if mem.get('skills_used') else 'none'}

## Metrics

| Metric | Value |
|--------|-------|
| Model | {mn} |
| Cost | ${meta[2]:.4f} |
| Input Tokens | {meta[3]} |
| Output Tokens | {meta[4]} |

---
*Generated by DeepSeek Flash*
"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    fn = f"{MEMORY_DIR}/{sid}.md"
    with open(fn, "w") as f:
        f.write(card)
    return fn


def update_index():
    if not os.path.exists(MEMORY_DIR): return
    cards = []
    for f in sorted(os.listdir(MEMORY_DIR)):
        if not f.endswith(".md"): continue
        with open(f"{MEMORY_DIR}/{f}") as cf:
            c = cf.read()
        tm = re.search(r"^# (.+)$", c, re.MULTILINE)
        dm = re.search(r"^date: (.+)$", c, re.MULTILINE)
        cm = re.search(r"^confidence: (.+)$", c, re.MULTILINE)
        cards.append((f.replace(".md",""), tm.group(1) if tm else f, dm.group(1) if dm else "-", cm.group(1) if cm else "-"))

    idx = f"""# Session Memory Index

> Auto-generated by walter-worker-session-memory (DeepSeek Flash).

**Total:** {len(cards)}

| Date | Title | Confidence | File |
|------|-------|------------|------|
"""
    for sid, title, date, conf in cards:
        idx += f"| {date} | {title} | {conf} | [[session-memory/{sid}\\|link]] |\n"
    idx += f"\n*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    with open(f"{VAULT_PATH}/Session Memory Index.md", "w") as f:
        f.write(idx)


def process_one(sid, title, model_raw, cost, tok_in, tok_out, ts, score_mode):
    db = sqlite3.connect(DB_PATH)
    parts = extract_parts(db, sid)
    db.close()

    if len(parts) < 3 or sum(len(p) for p in parts) < 500:
        return ("skip", sid, title, None, None)

    txt = "\n\n".join(parts)
    if len(parts) > 60:
        txt = "\n\n".join(parts[:30] + parts[-15:])

    try:
        result = api_call(EXTRACT_PROMPT, txt)
    except Exception as e:
        return ("fail_api", sid, title, None, str(e)[:80])

    mem = extract_json(result)
    if not mem:
        return ("fail_json", sid, title, None, result[:60] if result else "empty")

    meta = (ts, model_raw, cost, tok_in, tok_out)
    fn = write_card(sid, title, mem, meta)

    score = None
    if score_mode and mem:
        try:
            sr = api_call(EVAL_PROMPT, json.dumps(mem, ensure_ascii=False, indent=2), temp=0.1, maxtok=512)
            score = extract_json(sr)
        except: pass

    return ("ok", sid, title, float(mem.get("confidence", 0.5)), score)


def main():
    force = "--force" in sys.argv
    score_mode = "--score" in sys.argv
    limit = None
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i+1 < len(sys.argv):
            limit = int(sys.argv[i+1])

    print(f"[*] Model: DeepSeek Flash | Workers: {WORKERS}", flush=True)

    os.makedirs(VAULT_PATH, exist_ok=True)

    existing = set()
    if not force and os.path.exists(MEMORY_DIR):
        for f in os.listdir(MEMORY_DIR):
            if f.endswith(".md"): existing.add(f.replace(".md",""))

    db = sqlite3.connect(DB_PATH)
    sessions = db.execute("""
        SELECT s.id, s.title, s.time_created, s.model, s.cost, s.tokens_input, s.tokens_output
        FROM session s WHERE s.title IS NOT NULL AND s.title != ''
        ORDER BY s.tokens_input DESC
    """).fetchall()
    db.close()

    jobs = [(s[0], s[1], s[3], s[4], s[5], s[6], s[2]) for s in sessions if s[0] not in existing or force]
    if limit: jobs = jobs[:limit]

    print(f"[*] Total: {len(sessions)}, To process: {len(jobs)}", flush=True)
    if not jobs:
        print("[*] Nothing to do.")
        return

    stats = {"ok": 0, "skip": 0, "fail_api": 0, "fail_json": 0}
    scores = []
    t0 = time.time()
    done = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process_one, *j, score_mode): j for j in jobs}
        for fut in as_completed(futs):
            done += 1
            status, sid, title, conf, score = fut.result()
            stats[status] = stats.get(status, 0) + 1

            icon = {"ok": "+", "skip": "~", "fail_api": "x", "fail_json": "j"}.get(status, "?")
            extra = ""
            if isinstance(score, dict) and score.get("total"):
                scores.append(score)
                extra = f" score={score['total']}/100"
            elif conf is not None:
                extra = f" conf={float(conf):.2f}"

            rem = len(jobs) - done
            eta = (time.time() - t0) / done * rem if done > 0 else 0
            print(f"[{done}/{len(jobs)}] {icon} {title[:55]:55s} {extra} | ETA {eta/60:.0f}m | ${total_cost:.4f}", flush=True)

    update_index()

    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"Done in {elapsed/60:.1f}m")
    for k, v in stats.items():
        print(f"  {k:20s}: {v}")
    print(f"  Total API cost:     ${total_cost:.4f}")
    if scores:
        avg = sum(s.get("total", 0) for s in scores) / len(scores)
        p80 = sum(1 for s in scores if s.get("total", 0) >= 80)
        print(f"  Avg score:          {avg:.1f}/100")
        print(f"  >= 80:              {p80}/{len(scores)}")
    print(f"  Written to:         {MEMORY_DIR}/")


if __name__ == "__main__":
    main()
