#!/usr/bin/env python3
"""
Simple Anthropic-to-OpenAI Bridge for Keymaster - WITH TOOL CALL SUPPORT + CDP WEB TOOLS
"""

import json
import os
import sys
import re
import uuid
import asyncio
import websockets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx

KEYMASTER_URL = os.getenv("KEYMASTER_URL", "http://127.0.0.1:8787")
CDP_URL = os.getenv("CDP_URL", "http://localhost:9222")

MODEL_MAP = {
    "claude-sonnet-4-6": "moonshotai/kimi-k2.5",
    "claude-opus-4-6": "moonshotai/kimi-k2.5",
    "claude-haiku-4-5": "moonshotai/kimi-k2.5",
    "claude-haiku-4-5-20251001": "moonshotai/kimi-k2.5",
    "sonnet": "moonshotai/kimi-k2.5",
    "opus": "moonshotai/kimi-k2.5",
    "haiku": "moonshotai/kimi-k2.5",
}

WEB_TOOLS = [
    {
        "name": "web_fetch",
        "description": "Fetch a URL using a real Chrome browser. Returns fully rendered page text including JavaScript-rendered content. Use this to read any webpage, article, or web resource.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web using Google via a real Chrome browser. Returns search result titles, URLs and snippets. Use this to find current information, news, or any topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    }
]

BRIDGE_TOOL_NAMES = {t["name"] for t in WEB_TOOLS}
http_client: httpx.AsyncClient = None


async def cdp_command(ws, method, params=None):
    cmd_id = int(uuid.uuid4().int % 100000)
    cmd = {"id": cmd_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(cmd))
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        if msg.get("id") == cmd_id:
            return msg.get("result", {})


async def cdp_fetch(url: str, max_chars: int = 15000) -> str:
    try:
        resp = await http_client.put(f"{CDP_URL}/json/new")
        tab = resp.json()
        ws_url = tab["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "Page.navigate", {"url": url})

            await asyncio.sleep(4)

            result = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """(function() {
                    ['script','style','nav','footer','header','aside'].forEach(tag => {
                        document.querySelectorAll(tag).forEach(el => el.remove());
                    });
                    return document.body ? document.body.innerText : document.documentElement.innerText;
                })()""",
                "returnByValue": True
            })

            await http_client.get(f"{CDP_URL}/json/close/{tab['id']}")
            text = result.get("result", {}).get("value", "")
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            return text[:max_chars]

    except Exception as e:
        return f"Error fetching {url}: {e}"


async def cdp_search(query: str, max_chars: int = 10000) -> str:
    search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    try:
        resp = await http_client.put(f"{CDP_URL}/json/new")
        tab = resp.json()
        ws_url = tab["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "Page.navigate", {"url": search_url})

            await asyncio.sleep(3)

            result = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """(function() {
                    const results = [];
                    document.querySelectorAll('.result').forEach((el, i) => {
                        if (i > 10) return;
                        const title = el.querySelector('.result__title');
                        const link = el.querySelector('.result__url');
                        const snippet = el.querySelector('.result__snippet');
                        if (title) {
                            results.push({
                                title: title.innerText.trim(),
                                url: link ? link.innerText.trim() : '',
                                snippet: snippet ? snippet.innerText.trim() : ''
                            });
                        }
                    });
                    return JSON.stringify(results);
                })()""",
                "returnByValue": True
            })

            await http_client.get(f"{CDP_URL}/json/close/{tab['id']}")
            raw = result.get("result", {}).get("value", "[]")
            try:
                items = json.loads(raw)
                if not items:
                    return await cdp_fetch(search_url)
                lines = [f"**{item['title']}**\n{item['url']}\n{item['snippet']}\n" for item in items]
                return "\n".join(lines)[:max_chars]
            except:
                return raw[:max_chars]

    except Exception as e:
        return f"Error searching '{query}': {e}"


async def execute_tool(name: str, arguments: dict) -> str:
    print(f"[BRIDGE] Tool: {name} args={arguments}", file=sys.stderr, flush=True)
    if name == "web_fetch":
        return await cdp_fetch(arguments.get("url", ""))
    elif name == "web_search":
        return await cdp_search(arguments.get("query", ""))
    return f"Unknown tool: {name}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(600.0, connect=30.0, read=300.0, write=300.0, pool=300.0),
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        follow_redirects=True
    )
    print("[BRIDGE] HTTP client started", file=sys.stderr, flush=True)
    yield
    await http_client.aclose()
    print("[BRIDGE] HTTP client closed", file=sys.stderr, flush=True)

app = FastAPI(lifespan=lifespan)


@app.get("/cdp/search")
async def cdp_search_endpoint(q: str = ""):
    if not q:
        return JSONResponse(content={"error": "no query"}, status_code=400)
    result = await cdp_search(q)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(result)

@app.get("/cdp/fetch")
async def cdp_fetch_endpoint(url: str = ""):
    if not url:
        return JSONResponse(content={"error": "no url"}, status_code=400)
    result = await cdp_fetch(url)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(result)

@app.get("/health")
async def health():
    return {"status": "ok", "keymaster": KEYMASTER_URL}


def convert_messages(body):
    msgs = []
    if "system" in body:
        system = body["system"]
        if isinstance(system, list):
            system = "\n".join(b.get("text", "") for b in system if isinstance(b, dict))
        msgs.append({"role": "system", "content": system})

    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, list):
            tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
            text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]

            if tool_results:
                for tr in tool_results:
                    tr_content = tr.get("content", "")
                    if isinstance(tr_content, list):
                        tr_content = "\n".join(b.get("text", "") for b in tr_content if isinstance(b, dict))
                    msgs.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", "call_0"),
                        "content": tr_content
                    })
                continue

            tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            if tool_uses and role == "assistant":
                msgs.append({
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else None,
                    "tool_calls": [
                        {
                            "id": tu.get("id", "call_0"),
                            "type": "function",
                            "function": {
                                "name": tu.get("name", ""),
                                "arguments": json.dumps(tu.get("input", {}))
                            }
                        }
                        for tu in tool_uses
                    ]
                })
                continue

            content = "\n".join(text_parts)

        msgs.append({"role": "assistant" if role == "assistant" else "user", "content": content})

    return msgs


def build_openai_body(body, anthropic_model):
    openai_body = {
        "model": MODEL_MAP.get(anthropic_model, "moonshotai/kimi-k2.5"),
        "messages": convert_messages(body),
        "max_tokens": body.get("max_tokens", 4096),
        "temperature": body.get("temperature", 0.7),
        "stream": body.get("stream", False)
    }

    all_tools = list(body.get("tools", []))
    existing_names = {t["name"] for t in all_tools}
    for wt in WEB_TOOLS:
        if wt["name"] not in existing_names:
            all_tools.append(wt)

    if all_tools:
        openai_body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            }
            for t in all_tools
        ]
        openai_body["tool_choice"] = "auto"

    return openai_body


@app.post("/v1/messages")
async def messages(request: Request):
    try:
        body = await request.json()
        anthropic_model = body.get("model", "sonnet")
        stream = body.get("stream", False)

        print(f"[BRIDGE] {anthropic_model} stream={stream}", file=sys.stderr, flush=True)

        openai_body = build_openai_body(body, anthropic_model)
        headers = {"Content-Type": "application/json"}

        if stream:
            async def generate():
                msg_id = "msg_bridge"
                yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': anthropic_model}})}\n\n"
                yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

                full_content = ""
                tool_call_chunks = {}

                async with http_client.stream("POST",
                                              f"{KEYMASTER_URL}/v1/chat/completions",
                                              json=openai_body,
                                              headers=headers) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    full_content += text
                                    yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}})}\n\n"
                                for tc in delta.get("tool_calls", []):
                                    idx = tc.get("index", 0)
                                    if idx not in tool_call_chunks:
                                        tool_call_chunks[idx] = {"id": tc.get("id", f"call_{idx}"), "name": "", "arguments": ""}
                                    if tc.get("function", {}).get("name"):
                                        tool_call_chunks[idx]["name"] += tc["function"]["name"]
                                    if tc.get("function", {}).get("arguments"):
                                        tool_call_chunks[idx]["arguments"] += tc["function"]["arguments"]
                            except Exception as parse_err:
                                print(f"[BRIDGE] Parse error: {parse_err} raw={data[:200]}", file=__import__('sys').stderr, flush=True)

                # Always emit a text delta before stopping index 0 so Claude Code never sees null text
                if not full_content:
                    yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': ' '}})}\n\n"
                yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                if tool_call_chunks:
                    for i, (idx, tc) in enumerate(tool_call_chunks.items(), start=1):
                        yield f"data: {json.dumps({'type': 'content_block_start', 'index': i, 'content_block': {'type': 'tool_use', 'id': tc['id'], 'name': tc['name'], 'input': {}}})}\n\n"
                        yield f"data: {json.dumps({'type': 'content_block_delta', 'index': i, 'delta': {'type': 'input_json_delta', 'partial_json': tc['arguments']}})}\n\n"
                        yield f"data: {json.dumps({'type': 'content_block_stop', 'index': i})}\n\n"
                    stop_reason = "tool_use"
                else:
                    stop_reason = "end_turn"

                yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason}, 'usage': {'output_tokens': len(full_content) // 4}})}\n\n"
                yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

        else:
            resp = await http_client.post(f"{KEYMASTER_URL}/v1/chat/completions",
                                          json=openai_body,
                                          headers=headers)
            openai_resp = resp.json()
            message = openai_resp["choices"][0]["message"]
            content_blocks = []

            if message.get("tool_calls"):
                content_blocks.append({"type": "text", "text": message.get("content") or ""})

                bridge_calls = [tc for tc in message["tool_calls"] if tc["function"]["name"] in BRIDGE_TOOL_NAMES]
                passthrough_calls = [tc for tc in message["tool_calls"] if tc["function"]["name"] not in BRIDGE_TOOL_NAMES]

                if bridge_calls:
                    tool_results = []
                    for tc in bridge_calls:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except:
                            args = {}
                        result = await execute_tool(tc["function"]["name"], args)
                        tool_results.append({"tool_call_id": tc["id"], "content": result})
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": args
                        })

                    new_messages = openai_body["messages"] + [
                        {"role": "assistant", "content": message.get("content") or "", "tool_calls": bridge_calls}
                    ]
                    for tr in tool_results:
                        new_messages.append({"role": "tool", "tool_call_id": tr["tool_call_id"], "content": tr["content"]})

                    followup_body = {**openai_body, "messages": new_messages, "stream": False}
                    followup_resp = await http_client.post(f"{KEYMASTER_URL}/v1/chat/completions",
                                                           json=followup_body, headers=headers)
                    final_text = followup_resp.json()["choices"][0]["message"].get("content", "")
                    return JSONResponse(content={
                        "id": openai_resp.get("id", "msg_bridge"),
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "text", "text": final_text}],
                        "model": anthropic_model,
                        "stop_reason": "end_turn",
                        "usage": {
                            "input_tokens": openai_resp.get("usage", {}).get("prompt_tokens", 0),
                            "output_tokens": openai_resp.get("usage", {}).get("completion_tokens", 0)
                        }
                    })

                for tc in passthrough_calls:
                    try:
                        input_data = json.loads(tc["function"]["arguments"])
                    except:
                        input_data = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": input_data
                    })
                stop_reason = "tool_use"

            else:
                content_blocks.append({"type": "text", "text": message.get("content", "")})
                stop_reason = "end_turn"

            return JSONResponse(content={
                "id": openai_resp.get("id", "msg_bridge"),
                "type": "message",
                "role": "assistant",
                "content": content_blocks,
                "model": anthropic_model,
                "stop_reason": stop_reason,
                "usage": {
                    "input_tokens": openai_resp.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": openai_resp.get("usage", {}).get("completion_tokens", 0)
                }
            })

    except Exception as e:
        import traceback
        print(f"[BRIDGE ERROR] {e}\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        return JSONResponse(status_code=500, content={"error": "Bridge Error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8789, log_level="info")
