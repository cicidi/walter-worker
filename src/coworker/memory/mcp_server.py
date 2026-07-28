"""MCP server for Memory Graph — exposes graph query as a native tool.

Claude Code can call query_memory_graph directly instead of running
coworker memory query as a bash command.

Usage (add to ~/.coworker/coworker.yaml):
  mcp:
    - name: memory-graph
      command: python3
      args: ["-m", "coworker.memory.mcp_server"]
"""

from __future__ import annotations

import json
import sys
import logging

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger(__name__)


def query_graph(query: str, top_k: int = 10) -> list[dict]:
    """Query the memory graph for relevant nodes."""
    try:
        from .storage import load_graph
        from .query import search_graph
        g = load_graph()
        if not g.nodes:
            return []
        return search_graph(g, query, top_k=top_k)
    except Exception as e:
        logger.error("Graph query failed: %s", e)
        return []


def graph_stats() -> dict:
    """Return graph statistics."""
    try:
        from .storage import load_graph
        g = load_graph()
        node_types = {}
        for n in g.nodes:
            t = n.type or "unknown"
            node_types[t] = node_types.get(t, 0) + 1
        return {
            "total_nodes": len(g.nodes),
            "total_edges": len(g.links),
            "by_type": node_types,
        }
    except Exception as e:
        return {"error": str(e)}


def search_mem0(query: str, top_k: int = 5) -> list[dict]:
    """Search mem0 vector memory for relevant past lessons and patterns."""
    try:
        from .mem0_client import Mem0Client
        client = Mem0Client.from_config()
        results = client.search(query=query, top_k=top_k)
        return [
            {"memory": r.get("memory", ""), "type": r.get("metadata", {}).get("type", "?"), "score": r.get("score", 0)}
            for r in results
        ]
    except Exception as e:
        logger.error("mem0 search failed: %s", e)
        return []


def handle_request(req: dict) -> dict | None:
    """Handle a single JSON-RPC request. Returns response or None for notifications."""
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "memory-graph", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "query_memory_graph",
                        "description": "Query the project's memory knowledge graph. Returns relevant code nodes, document references, and their relationships. Use this to find which files relate to a feature, what calls what, or architectural patterns. The graph has 2,595 code/document nodes and 5,126 edges.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "What to search for — a feature name, file path, concept, or question",
                                },
                                "top_k": {
                                    "type": "integer",
                                    "description": "Max results (default 10)",
                                    "default": 10,
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "search_memory",
                        "description": "Search past session memories (mem0 vector store). Returns relevant lessons, patterns, conventions, and decisions from all past sessions. Use this to find prior experience, mistakes to avoid, or successful approaches.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "What to search for — describe the problem, pattern, or topic",
                                },
                                "top_k": {
                                    "type": "integer",
                                    "description": "Max results (default 5)",
                                    "default": 5,
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "memory_graph_stats",
                        "description": "Get statistics about the memory graph: total nodes, edges, and breakdown by type.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            },
        }

    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "query_memory_graph":
            results = query_graph(arguments.get("query", ""), arguments.get("top_k", 10))
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}],
                },
            }

        if tool_name == "search_memory":
            results = search_mem0(arguments.get("query", ""), arguments.get("top_k", 5))
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}],
                },
            }

        if tool_name == "memory_graph_stats":
            stats = graph_stats()
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(stats, indent=2, ensure_ascii=False)}],
                },
            }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    """Run the MCP server on stdio."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        if resp:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
