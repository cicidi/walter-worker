import type { Hooks, PluginInput } from "@opencode-ai/plugin"
import { tool } from "@opencode-ai/plugin"
import { createSession } from "./session"
import { Recorder } from "./recorder"
import { writeFileSync, mkdirSync, existsSync, readFileSync } from "fs"
import { join } from "path"
import { homedir } from "os"
import { execSync } from "child_process"

const STATUS_BASE = join(homedir(), ".coworker", "status")
const OPENCODE_STATE = join(STATUS_BASE, "opencode", "current.state")

const MODEL_MAX_CONTEXT: Record<string, number> = {
  "deepseek-v4-pro": 128000,
  "deepseek-chat": 128000,
  "deepseek-reasoner": 128000,
  "claude-sonnet-4-20250514": 200000,
  "claude-3-opus-20240229": 200000,
  "claude-3-5-sonnet-20241022": 200000,
  "gemini-2.5-pro": 1048576,
  "gemini-2.5-flash": 1048576,
  "gpt-4o": 128000,
  "glm-5.2": 128000,
}

function getMaxContext(modelID: string): number {
  for (const [key, val] of Object.entries(MODEL_MAX_CONTEXT)) {
    if (modelID.includes(key)) return val
  }
  return 128000
}

function ensureStateDir() {
  const dir = join(STATUS_BASE, "opencode")
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
}

function writeState(data: Record<string, string>) {
  try {
    ensureStateDir()
    let content = ""
    for (const [k, v] of Object.entries(data)) {
      if (v !== undefined && v !== null) content += `${k}=${v}\n`
    }
    writeFileSync(OPENCODE_STATE, content)
  } catch {}
}

let currentModel = ""
let currentMode = ""
let currentEffort = ""
let cumulativeCost = 0
let currentProject = ""
let currentBranch = ""
let currentPath = ""

export default {
  id: "coworker-analytics",

  server(input: PluginInput): Hooks {
    let currentRecorder: Recorder | null = null
    let currentSessionId: string | null = null
    const $ = input.$
    const cwd = input.directory || process.cwd()

    try {
      execSync("git rev-parse --git-dir", { cwd, timeout: 2000 })
    } catch {}

    let project = ""
    let branch = ""
    try {
      project = execSync("git rev-parse --show-toplevel", { cwd, timeout: 2000 }).toString().trim()
      project = project.split("/").pop() || project
      branch = execSync("git rev-parse --abbrev-ref HEAD", { cwd, timeout: 2000 }).toString().trim()
    } catch {}
    currentProject = project
    currentBranch = branch
    currentPath = cwd

    writeState({
      session_id: "",
      mode: "Build",
      model: "",
      effort: "",
      ctx_pct: "0%",
      cost: "0",
      project,
      branch,
      path: cwd,
      updated: new Date().toISOString(),
    })

    return {
      async event({ event }) {
        try {
          if (event.type === "session.created") {
            const { id, recorder } = createSession(cwd, "opencode")
            currentSessionId = id
            currentRecorder = recorder
            cumulativeCost = 0
            currentModel = ""
            currentMode = ""
            currentEffort = ""

            let sp = ""
            let sb = ""
            try {
              sp = execSync("git rev-parse --show-toplevel", { cwd, timeout: 2000 }).toString().trim()
              sp = sp.split("/").pop() || sp
              sb = execSync("git rev-parse --abbrev-ref HEAD", { cwd, timeout: 2000 }).toString().trim()
            } catch {}
            currentProject = sp
            currentBranch = sb

            writeState({
              session_id: id,
              mode: "",
              model: "",
              effort: "",
              ctx_pct: "0",
              cost: "0",
              project: sp,
              branch: sb,
              path: cwd,
              updated: new Date().toISOString(),
            })
          }
        } catch {}
      },

      "chat.message"(input, output) {
        if (!currentRecorder) return
        try {
          const msg = output.message
          const type = msg.role === "user" ? "user" : "assistant"
          const content = (msg as any).parts?.map((p: any) => p.text || p.tool_use?.name || "").filter(Boolean).join(" ") || ""
          currentRecorder.writeJSONL("messages.jsonl", {
            ts: new Date().toISOString(),
            type,
            seq: currentRecorder.nextSeq(),
            content: content.slice(0, 5000),
          })

          if (type === "assistant") {
            const amsg = msg as any
            if (amsg.cost !== undefined) cumulativeCost = amsg.cost
            if (amsg.mode) currentMode = amsg.mode.charAt(0).toUpperCase() + amsg.mode.slice(1)
            if (amsg.modelID) currentModel = amsg.modelID

            const tokens = amsg.tokens
            const ctxPct = tokens?.input ? Math.round((tokens.input / getMaxContext(currentModel)) * 100) + "%" : "0%"

            writeState({
              session_id: currentSessionId || "",
              mode: currentMode || "Build",
              model: currentModel,
              effort: currentEffort,
              ctx_pct: ctxPct,
              cost: String(cumulativeCost),
              project: currentProject,
              branch: currentBranch,
              path: currentPath,
              updated: new Date().toISOString(),
            })
          } else {
            if (input.model?.modelID) currentModel = input.model.modelID
            if (input.agent) currentMode = input.agent.charAt(0).toUpperCase() + input.agent.slice(1)
            if (input.variant) {
              if (input.variant.includes("high")) currentEffort = "high"
              else if (input.variant.includes("medium")) currentEffort = "medium"
              else if (input.variant.includes("low")) currentEffort = "low"
              else currentEffort = input.variant
            }

            writeState({
              session_id: currentSessionId || "",
              mode: currentMode || "Build",
              model: currentModel,
              effort: currentEffort,
              ctx_pct: "0%",
              cost: String(cumulativeCost),
              project: currentProject,
              branch: currentBranch,
              path: currentPath,
              updated: new Date().toISOString(),
            })
          }
        } catch {}
      },

      tool: {
        coworker_status: tool({
          description: "Get current AI session status including mode, model, effort, context usage percentage, cost, project, and branch",
          args: {},
          async execute() {
            try {
              if (existsSync(OPENCODE_STATE)) {
                const content = readFileSync(OPENCODE_STATE, "utf-8")
                const lines = content.trim().split("\n")
                const data: Record<string, string> = {}
                for (const line of lines) {
                  const eq = line.indexOf("=")
                  if (eq > 0) data[line.slice(0, eq)] = line.slice(eq + 1)
                }
                return [
                  `Mode: ${data.mode || "?"}  |  Model: ${data.model || "?"}  |  Effort: ${data.effort || "?"}`,
                  `Context: ${data.ctx_pct || "0%"} used  |  Cost: $${data.cost || "0"}`,
                  data.project ? `Project: ${data.project}  |  Branch: ${data.branch || "?"}` : "",
                  `Path: ${data.path || "?"}`,
                  `Session: ${data.session_id || "?"}`,
                  `Updated: ${data.updated || "?"}`,
                ].filter(Boolean).join("\n")
              }
              return "No active OpenCode session state."
            } catch {
              return "Unable to read session state."
            }
          },
        }),
      },

      "tool.execute.before"(input, output) {
        if (!currentRecorder) return
        try {
          currentRecorder.writeJSONL("tools.jsonl", {
            ts: new Date().toISOString(),
            phase: "before",
            tool: input.tool,
            tool_type: "builtin",
            call_id: input.callID,
            seq: currentRecorder.nextSeq(),
            args: output.args,
          })
        } catch {}
      },

      "tool.execute.after"(input, output) {
        if (!currentRecorder) return
        try {
          currentRecorder.writeJSONL("tools.jsonl", {
            ts: new Date().toISOString(),
            phase: "after",
            tool: input.tool,
            tool_type: "builtin",
            call_id: input.callID,
            seq: currentRecorder.nextSeq(),
            result: typeof output.output === "string" ? output.output.slice(0, 10000) : JSON.stringify(output.output).slice(0, 10000),
            duration_ms: output.metadata?.duration || 0,
          })
        } catch {}
      },

      "experimental.session.compacting"(_input, _output) {
        if (currentRecorder) {
          try {
            currentRecorder.writeSessionYaml({ compacted: new Date().toISOString() })
          } catch {}
        }
        if ($) {
          try {
            $.nothrow()`coworker state-update`.quiet()
          } catch {}
        }
      },
    }
  },
}
