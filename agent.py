import ollama
import datetime
import os
import sys
from system_prompt import SYSTEM_PROMPT

# ANSI colors (work on Windows 10+ and all Unix terminals)
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

MODEL = "llama3.2"

def save_one_pager(content: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"my_offer_{timestamp}.txt"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def extract_one_pager(text: str) -> str | None:
    start_tag = "[ONE-PAGER-START]"
    end_tag = "[ONE-PAGER-END]"
    start = text.find(start_tag)
    end = text.find(end_tag)
    if start != -1 and end != -1:
        return text[start + len(start_tag):end].strip()
    return None

def print_banner():
    print(f"""
{CYAN}{BOLD}
╔══════════════════════════════════════════════════╗
║         NOVA — Your AI Business Coach           ║
║      Millionaire Roadmap  •  Phase 1: Ideation  ║
╚══════════════════════════════════════════════════╝
{RESET}
{YELLOW}Type your message and press Enter. Type 'quit' to exit.{RESET}
""")

def check_ollama_model():
    try:
        models = ollama.list()
        available = [m.model for m in models.models]
        if not any(MODEL in m for m in available):
            print(f"{YELLOW}Model '{MODEL}' not found. Pulling it now (first-time only, ~2GB)...{RESET}\n")
            for chunk in ollama.pull(MODEL, stream=True):
                if hasattr(chunk, 'status'):
                    print(f"\r{chunk.status}", end="", flush=True)
            print(f"\n{GREEN}Model ready!{RESET}\n")
    except Exception as e:
        print(f"\n{YELLOW}Could not connect to Ollama. Make sure Ollama is running.{RESET}")
        print(f"Download it free at: https://ollama.com\n")
        print(f"Then run: ollama pull {MODEL}\n")
        sys.exit(1)

def chat():
    print_banner()
    check_ollama_model()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    one_pager_saved = False

    print(f"{CYAN}{BOLD}Nova:{RESET} ", end="", flush=True)

    # Initial greeting from Nova
    opening = ollama.chat(
        model=MODEL,
        messages=messages,
        stream=True
    )
    full_response = ""
    for chunk in opening:
        token = chunk.message.content
        print(token, end="", flush=True)
        full_response += token
    print("\n")

    messages.append({"role": "assistant", "content": full_response})

    while True:
        try:
            user_input = input(f"{YELLOW}{BOLD}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{GREEN}Nova: Great session! Come back anytime. Good luck!{RESET}\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print(f"\n{GREEN}Nova: Great session! Come back anytime. Good luck!{RESET}\n")
            break

        messages.append({"role": "user", "content": user_input})

        print(f"\n{CYAN}{BOLD}Nova:{RESET} ", end="", flush=True)

        stream = ollama.chat(
            model=MODEL,
            messages=messages,
            stream=True
        )

        full_response = ""
        for chunk in stream:
            token = chunk.message.content
            print(token, end="", flush=True)
            full_response += token

        print("\n")
        messages.append({"role": "assistant", "content": full_response})

        # Detect and save one-pager
        if not one_pager_saved:
            one_pager = extract_one_pager(full_response)
            if one_pager:
                filepath = save_one_pager(one_pager)
                print(f"{GREEN}{BOLD}[Nova has saved your offer one-pager to: {filepath}]{RESET}\n")
                one_pager_saved = True

if __name__ == "__main__":
    chat()
