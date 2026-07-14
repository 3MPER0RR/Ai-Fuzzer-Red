#!/usr/bin/env python3
"""
ZeroAgent v0.2 — minimal multi-provider AI client con function calling
Supporta: Claude, Groq, OpenRouter, Ollama
Zero dipendenze esterne — Python 3.8+
"""

import os, json, ssl, urllib.request, urllib.error
import subprocess, platform, sys

# Fix SSL macOS
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl._create_unverified_context()

# Provider config
PROVIDERS = {
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-6"
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "qwen/qwen3-32b"
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "model": "mistralai/mistral-7b-instruct"
    },
    "ollama": {
        "url": "https://ollama.com/api/chat",
        "key_env": "OLLAMA_API_KEY",
        "model": "nemotron-3-ultra:cloud"
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash"
    },
}

# Tool definitions - formato OpenAI
TOOLS_OPENAI = [
    {"type":"function","function":{"name":"get_system_info","description":"Info sistema locale (OS, CPU, RAM)","parameters":{"type":"object","properties":{"detail":{"type":"string","enum":["os","cpu","ram","all"]}},"required":["detail"]}}},
    {"type":"function","function":{"name":"run_shell","description":"Esegue un singolo comando shell","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
    {"type":"function","function":{"name":"nmap_scan","description":"Scansione nmap su host o range IP","parameters":{"type":"object","properties":{"target":{"type":"string"},"flags":{"type":"string"}},"required":["target"]}}},
    {"type":"function","function":{"name":"whois_lookup","description":"Whois su dominio o IP","parameters":{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]}}},
    {"type":"function","function":{"name":"dns_lookup","description":"Risolve record DNS di un dominio","parameters":{"type":"object","properties":{"target":{"type":"string"},"record_type":{"type":"string","enum":["A","MX","NS","TXT","CNAME","ANY"]}},"required":["target"]}}},
    {"type":"function","function":{"name":"http_headers","description":"Recupera header HTTP di un URL (banner grabbing)","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
    {"type":"function","function":{"name":"ping_host","description":"Ping su un host","parameters":{"type":"object","properties":{"target":{"type":"string"},"count":{"type":"integer"}},"required":["target"]}}},
    {"type":"function","function":{"name":"traceroute","description":"Traceroute verso un host","parameters":{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]}}},
    {"type":"function","function":{"name":"curl_request","description":"Richiesta HTTP GET o POST","parameters":{"type":"object","properties":{"url":{"type":"string"},"method":{"type":"string","enum":["GET","POST"]},"data":{"type":"string"},"extra_headers":{"type":"string"}},"required":["url"]}}},
    {"type":"function","function":{"name":"read_file","description":"Legge un file locale","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
    {"type":"function","function":{"name":"write_file","description":"Scrive o appende contenuto in un file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"mode":{"type":"string","enum":["write","append"]}},"required":["path","content"]}}},
]

# Tool definitions - formato Claude
TOOLS_CLAUDE = [
    {"name":"get_system_info","description":"Info sistema locale (OS, CPU, RAM)","input_schema":{"type":"object","properties":{"detail":{"type":"string","enum":["os","cpu","ram","all"]}},"required":["detail"]}},
    {"name":"run_shell","description":"Esegue un singolo comando shell","input_schema":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}},
    {"name":"nmap_scan","description":"Scansione nmap su host o range IP","input_schema":{"type":"object","properties":{"target":{"type":"string"},"flags":{"type":"string"}},"required":["target"]}},
    {"name":"whois_lookup","description":"Whois su dominio o IP","input_schema":{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]}},
    {"name":"dns_lookup","description":"Risolve record DNS di un dominio","input_schema":{"type":"object","properties":{"target":{"type":"string"},"record_type":{"type":"string","enum":["A","MX","NS","TXT","CNAME","ANY"]}},"required":["target"]}},
    {"name":"http_headers","description":"Recupera header HTTP di un URL (banner grabbing)","input_schema":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
    {"name":"ping_host","description":"Ping su un host","input_schema":{"type":"object","properties":{"target":{"type":"string"},"count":{"type":"integer"}},"required":["target"]}},
    {"name":"traceroute","description":"Traceroute verso un host","input_schema":{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]}},
    {"name":"curl_request","description":"Richiesta HTTP GET o POST","input_schema":{"type":"object","properties":{"url":{"type":"string"},"method":{"type":"string","enum":["GET","POST"]},"data":{"type":"string"},"extra_headers":{"type":"string"}},"required":["url"]}},
    {"name":"read_file","description":"Legge un file locale","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"write_file","description":"Scrive o appende contenuto in un file","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"mode":{"type":"string","enum":["write","append"]}},"required":["path","content"]}},
]


def execute_tool(name: str, args: dict) -> str:

    if name == "get_system_info":
        detail = args.get("detail", "all")
        info = {}
        if detail in ("os", "all"):
            info["os"] = platform.system()
            info["os_version"] = platform.version()
            info["machine"] = platform.machine()
        if detail in ("cpu", "all"):
            info["cpu"] = platform.processor()
        if detail in ("ram", "all"):
            try:
                if platform.system() == "Darwin":
                    r = subprocess.run(["sysctl","-n","hw.memsize"], capture_output=True, text=True)
                    info["ram_gb"] = round(int(r.stdout.strip()) / (1024**3), 1)
                elif platform.system() == "Linux":
                    r = subprocess.run(["free","-m"], capture_output=True, text=True)
                    info["ram_info"] = r.stdout.split("\n")[1]
            except Exception:
                info["ram"] = "N/A"
        return json.dumps(info)

    elif name == "run_shell":
        cmd = args.get("command", "")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return (r.stdout or r.stderr)[:3000]
        except subprocess.TimeoutExpired:
            return "Timeout (30s)"
        except Exception as e:
            return str(e)

    elif name == "nmap_scan":
        target = args.get("target", "")
        flags  = args.get("flags", "-sV")
        try:
            r = subprocess.run(f"nmap {flags} {target}", shell=True,
                               capture_output=True, text=True, timeout=120)
            return (r.stdout or r.stderr)[:4000]
        except subprocess.TimeoutExpired:
            return "Timeout nmap (120s)"
        except Exception as e:
            return f"Errore nmap: {e}"

    elif name == "whois_lookup":
        target = args.get("target", "")
        try:
            r = subprocess.run(["whois", target], capture_output=True, text=True, timeout=20)
            return (r.stdout or r.stderr)[:3000]
        except Exception as e:
            return f"Errore whois: {e}"

    elif name == "dns_lookup":
        target      = args.get("target", "")
        record_type = args.get("record_type", "A")
        try:
            r = subprocess.run(["dig", "+short", target, record_type],
                               capture_output=True, text=True, timeout=10)
            output = r.stdout.strip()
            return output if output else "Nessun record trovato"
        except Exception:
            try:
                r = subprocess.run(["nslookup", f"-type={record_type}", target],
                                   capture_output=True, text=True, timeout=10)
                return (r.stdout or r.stderr)[:2000]
            except Exception as e:
                return f"Errore dns: {e}"

    elif name == "http_headers":
        url = args.get("url", "")
        try:
            r = subprocess.run(["curl", "-sI", "--max-time", "10", url],
                               capture_output=True, text=True, timeout=15)
            return (r.stdout or r.stderr)[:2000]
        except Exception as e:
            return f"Errore http_headers: {e}"

    elif name == "ping_host":
        target = args.get("target", "")
        count  = args.get("count", 4)
        flag   = "-c" if platform.system() != "Windows" else "-n"
        try:
            r = subprocess.run(["ping", flag, str(count), target],
                               capture_output=True, text=True, timeout=20)
            return (r.stdout or r.stderr)[:2000]
        except Exception as e:
            return f"Errore ping: {e}"

    elif name == "traceroute":
        target = args.get("target", "")
        cmd    = "traceroute" if platform.system() != "Windows" else "tracert"
        try:
            r = subprocess.run([cmd, target], capture_output=True, text=True, timeout=60)
            return (r.stdout or r.stderr)[:3000]
        except Exception as e:
            return f"Errore traceroute: {e}"

    elif name == "curl_request":
        url    = args.get("url", "")
        method = args.get("method", "GET")
        data   = args.get("data", "")
        extra  = args.get("extra_headers", "")
        cmd    = ["curl", "-s", "--max-time", "15", "-X", method]
        if extra:
            for h in extra.split(","):
                h = h.strip()
                if h:
                    cmd += ["-H", h]
        if method == "POST" and data:
            cmd += ["-d", data]
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return (r.stdout or r.stderr)[:3000]
        except Exception as e:
            return f"Errore curl: {e}"

    elif name == "read_file":
        path = args.get("path", "")
        try:
            with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
                return f.read()[:4000]
        except Exception as e:
            return f"Errore lettura: {e}"

    elif name == "write_file":
        path    = args.get("path", "")
        content = args.get("content", "")
        mode    = "a" if args.get("mode") == "append" else "w"
        try:
            with open(os.path.expanduser(path), mode, encoding="utf-8") as f:
                f.write(content)
            return f"OK — file scritto: {path}"
        except Exception as e:
            return f"Errore scrittura: {e}"

    return f"Tool '{name}' non trovato"


def http_post(url: str, headers: dict, payload: dict, debug: bool = False) -> dict:
    headers["User-Agent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")

    if debug:
        safe = {k: (v[:20]+"..." if k.lower() in ("x-api-key","authorization") else v)
                for k, v in headers.items()}
        print(f"\n[DEBUG] URL: {url}")
        print(f"[DEBUG] Headers: {json.dumps(safe, indent=2)}")
        print(f"[DEBUG] Payload keys: {list(payload.keys())}\n")

    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"HTTP {e.code} {e.reason} — {body}")


def call_provider(provider: str, messages: list, system: str = "", debug: bool = False) -> dict:
    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["key_env"]) if cfg["key_env"] else None

    if provider == "claude":
        payload = {
            "model": cfg["model"], "max_tokens": 2048,
            "system": system or "Sei un agente AI utile. Rispondi in italiano.",
            "messages": messages, "tools": TOOLS_CLAUDE
        }
        headers = {
            "x-api-key": key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    elif provider == "ollama":
        payload = {"model": cfg["model"], "messages": messages, "stream": False}
        headers = {"content-type": "application/json"}
    elif provider == "gemini":
        # Gemini usa formato proprio — convertiamo la history
        gemini_contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            text = m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])
            gemini_contents.append({"role": role, "parts": [{"text": text}]})
        payload = {
            "contents": gemini_contents,
            "systemInstruction": {
                "parts": [{"text": system or "Sei un agente AI utile. Rispondi in italiano."}]
            },
            "tools": [{
                "function_declarations": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"]
                    }
                    for t in TOOLS_CLAUDE
                ]
            }],
            "generationConfig": {"maxOutputTokens": 2048}
        }
        # Gemini: key nell'URL, non nell'header
        url_with_key = cfg["url"] + "?key=" + (key or "")
        return http_post(url_with_key, {"content-type": "application/json"}, payload, debug=debug)
    else:
        payload = {
            "model": cfg["model"], "messages": messages,
            "tools": TOOLS_OPENAI, "tool_choice": "auto"
        }
        headers = {
            "Authorization": f"Bearer {key or ''}",
            "content-type": "application/json"
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/3MPER0RR/ZeroAgent"
            headers["X-Title"]      = "ZeroAgent"

    return http_post(cfg["url"], headers, payload, debug=debug)


def handle_response(provider: str, result: dict, messages: list, system: str = "", debug: bool = False) -> str:

    if provider == "claude":
        content     = result.get("content", [])
        stop_reason = result.get("stop_reason", "")
        if debug:
            print(f"[DEBUG] stop_reason: {stop_reason}")

        if stop_reason == "end_turn":
            for block in content:
                if block.get("type") == "text":
                    return block["text"]
            return "[nessun testo]"

        if stop_reason == "tool_use":
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    print(f"  -> [tool] {block['name']}({json.dumps(block['input'])})")
                    output = execute_tool(block["name"], block["input"])
                    print(f"  <- [result] {output[:150]}\n")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": output
                    })
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user",      "content": tool_results})
            followup = call_provider("claude", messages, system=system, debug=debug)
            return handle_response("claude", followup, messages, system=system, debug=debug)

    elif provider == "ollama":
        return result.get("message", {}).get("content", "[nessuna risposta]")

    elif provider == "gemini":
        candidates = result.get("candidates", [])
        if not candidates:
            return "[nessuna risposta da Gemini]"
        parts = candidates[0].get("content", {}).get("parts", [])
        finish = candidates[0].get("finishReason", "STOP")

        if debug:
            print(f"[DEBUG] Gemini finishReason: {finish}")

        # Controlla se c\'e\'  una function call
        tool_results_gemini = []
        for part in parts:
            if "functionCall" in part:
                fn_name = part["functionCall"]["name"]
                fn_args = part["functionCall"].get("args", {})
                print(f"  -> [tool] {fn_name}({json.dumps(fn_args)})")
                output = execute_tool(fn_name, fn_args)
                print(f"  <- [result] {output[:150]}\n")
                tool_results_gemini.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"content": output}
                    }
                })

        if tool_results_gemini:
            # Reinvia i risultati a Gemini
            messages.append({"role": "assistant", "content": json.dumps(parts)})
            messages.append({"role": "tool",      "content": json.dumps(tool_results_gemini)})
            followup = call_provider("gemini", messages, system=system, debug=debug)
            return handle_response("gemini", followup, messages, system=system, debug=debug)

        # Risposta testuale
        for part in parts:
            if "text" in part:
                return part["text"]
        return "[nessun testo da Gemini]"

    else:
        choice        = result["choices"][0]
        message       = choice["message"]
        finish_reason = choice.get("finish_reason", "")
        if debug:
            print(f"[DEBUG] finish_reason: {finish_reason}")

        if finish_reason == "stop":
            return message.get("content", "[nessuna risposta]")

        if finish_reason == "tool_calls":
            messages.append(message)
            for tc in message.get("tool_calls", []):
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])
                print(f"  -> [tool] {fn_name}({json.dumps(fn_args)})")
                output = execute_tool(fn_name, fn_args)
                print(f"  <- [result] {output[:150]}\n")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": output
                })
            followup = call_provider(provider, messages, system=system, debug=debug)
            return handle_response(provider, followup, messages, system=system, debug=debug)

        return message.get("content", "[nessuna risposta]")

    return "[nessuna risposta]"


def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else "groq"
    debug    = "--debug" in sys.argv

    if provider not in PROVIDERS:
        print(f"Provider '{provider}' non supportato. Disponibili: {', '.join(PROVIDERS.keys())}")
        sys.exit(1)

    cfg = PROVIDERS[provider]
    if cfg["key_env"]:
        if not os.environ.get(cfg["key_env"]):
            print(f"[ERRORE] {cfg['key_env']} non impostata.")
            print(f"Esempio: export {cfg['key_env']}=la_tua_key")
            sys.exit(1)

    tools_list = [t["function"]["name"] for t in TOOLS_OPENAI] if provider != "gemini" else [t["name"] for t in TOOLS_CLAUDE]

    print(f"╔══════════════════════════════════════════╗")
    print(f"║  ZeroAgent v0.2 — {provider:<23}║")
    print(f"║  Model: {cfg['model']:<33}║")
    print(f"╚══════════════════════════════════════════╝")
    print(f"  Tools ({len(tools_list)}): {', '.join(tools_list)}")
    print(f"  Debug: {'ON' if debug else 'OFF  (--debug per attivare)'}")
    print(f"  'exit' per uscire\n")

    history = []
    system_prompt = (
        "Sei un agente AI per sicurezza offensiva e penetration testing. "
        "Hai accesso a tool di rete e sistema. Usali quando necessario per rispondere "
        "con dati reali. Rispondi sempre in italiano."
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArrivederci!")
            break

        if user_input.lower() in ("exit", "quit", "esci"):
            print("Arrivederci!")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        try:
            result   = call_provider(provider, history, system=system_prompt, debug=debug)
            response = handle_response(provider, result, history, system=system_prompt, debug=debug)
            history.append({"role": "assistant", "content": response})
            print(f"\nAI: {response}\n")
        except Exception as e:
            print(f"[Errore] {e}\n")

if __name__ == "__main__":
    main()