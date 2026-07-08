import type { Hooks, PluginInput } from "@opencode-ai/plugin"
import { createSession } from "./session"
import { Recorder } from "./recorder"

export default {
  id: "coworker-analytics",

  server(input: PluginInput): Hooks {
    let currentRecorder: Recorder | null = null
    let currentSessionId: string | null = null
    const $ = input.$

    return {
      async event({ event }) {
        try {
          if (event.type === "session.created") {
            const { id, recorder } = createSession(process.cwd(), "opencode")
            currentSessionId = id
            currentRecorder = recorder
          }
        } catch {}
      },

      "chat.message"(input, output) {
        if (!currentRecorder) return
        try {
          const msg = output.message
          const type = msg.role === "user" ? "user" : "assistant"
          const content = msg.parts?.map((p: any) => p.text || p.tool_use?.name || "").filter(Boolean).join(" ") || ""
          currentRecorder.writeJSONL("messages.jsonl", {
            ts: new Date().toISOString(),
            type,
            seq: currentRecorder.nextSeq(),
            content: content.slice(0, 5000),
          })
        } catch {}
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
