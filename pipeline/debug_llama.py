"""Debug what llama.cpp actually returns for Qwen3."""
import requests, json

URL = "http://localhost:11435/v1/chat/completions"

def test(label, messages, extra={}):
    print(f"\n{'='*50}")
    print(f"TEST: {label}")
    payload = {"model": "x", "messages": messages,
                "max_tokens": 200, "stream": False, **extra}
    try:
        r = requests.post(URL, json=payload, timeout=60)
        data = r.json()
        msg = data["choices"][0]["message"]
        print(f"  content:          {repr(msg.get('content',''))[:120]}")
        print(f"  reasoning_content:{repr(msg.get('reasoning_content',''))[:120]}")
        # Show any extra fields
        for k, v in msg.items():
            if k not in ("role","content","reasoning_content"):
                print(f"  {k}: {repr(str(v))[:80]}")
    except Exception as e:
        print(f"  ERROR: {e}")
        try: print(f"  raw: {r.text[:300]}")
        except: pass

# Test 1: plain request
test("plain - no thinking directive",
     [{"role":"user","content":"Return JSON: [1,2,3,4,5]"}])

# Test 2: /no_think flag in user message
test("/no_think in user message",
     [{"role":"user","content":"/no_think\nReturn JSON: [1,2,3,4,5]"}])

# Test 3: empty think block as assistant prefix
test("empty <think> prefix injected",
     [{"role":"user","content":"Return JSON: [1,2,3,4,5]"},
      {"role":"assistant","content":"<think>\n\n</think>\n"}])

# Test 4: /no_think in system
test("/no_think in system prompt",
     [{"role":"system","content":"/no_think"},
      {"role":"user","content":"Return JSON: [1,2,3,4,5]"}])

# Test 5: chat_template_kwargs to disable thinking
test("enable_thinking=false via extra body",
     [{"role":"user","content":"Return JSON: [1,2,3,4,5]"}],
     {"chat_template_kwargs": {"enable_thinking": False}})

print("\n" + "="*50)
