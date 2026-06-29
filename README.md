# AI Fuzzer 🚀

An automated Python 3 framework designed for **Adversarial Fuzzing** and security stress-testing on Large Language Models (LLMs). This tool applies advanced logical and semantic mutations (inspired by *Elder Plinius* research techniques) and concurrently distributes the payloads across three distinct environments: **Ollama** (local), **Groq** (Cloud LPU), and **OpenRouter** (Frontier Models).

## ⚠️ Disclaimer (Legal Notice)

**This tool is released strictly for academic research, authorized penetration testing, and defensive development purposes.**  
The author assumes no liability for any misuse, damage, or violation of the Terms of Service (ToS) of any API providers (OpenAI, Anthropic, Groq, OpenRouter, etc.) resulting from the execution of this script. Do not target models or systems without explicit prior authorization for Red Teaming activities.

---

## 🔥 Key Features

- **Multi-Infrastructure Distribution**: Evaluate the exact same adversarial payload simultaneously across local and cloud-based deployments.
- **Homoglyph Attack Engine (Cyrillic Mutation)**: Obfuscates sensitive keywords using lookalike Unicode characters to bypass superficial tokenizers.
- **XML Tag Injection**: Simulates structural system boundary constraints (`</system_prompt>`) to test logical guardrail overrides.
- **Base64 Encoding Obfuscation**: Encapsulates input strings to audit the model's internal multi-step decoding and execution path.
- **Fault-Tolerant Engine**: Native handling of connection timeouts, server crashes, and API errors to ensure uninterrupted fuzzing cycles.

## 🛠️ Requirements & Installation

The tool requires **Python 3.7+** and the `requests` library.

1. Clone the repository:
   ```bash
   git clone https://github.com
   cd your-repo-name
   ```

2. Install dependencies:
   ```bash
   pip3 install requests
   ```

3. (Optional) If you plan to test local open-source models, ensure [Ollama](https://ollama.com) is up and running on your machine:
   ```bash
   ollama run llama3
   ```

## 🚀 Configuration & Usage

Open the `ai_fuzzer.py` file with your preferred text editor and configure your API tokens at the top:

```python
export GROQ_API_KEY = "YOUR_REAL_GROQ_TOKEN"
export OPENROUTER_API_KEY = "YOUR_REAL_OPENROUTER_TOKEN"
```

Modify the `prompt_target` variable at the bottom of the script with the query you wish to analyze, then execute it from your terminal:

```bash
python3 ai_fuzzer.py
```

## 📊 Output Analysis

The terminal UI will display in real-time:
1. The original plaintext target prompt.
2. The mutation logic applied by the fuzzing engine.
3. Truncated output previews returned by each provider, allowing you to immediately map which models sustained their alignment and which ones were successfully jailbroken.
