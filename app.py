import re
import datetime
import streamlit as st
from groq import Groq, AuthenticationError
from system_prompt import SYSTEM_PROMPT

MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="MillionaireCoach", page_icon="💰", layout="centered")

st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; max-width: 780px; }

    .free-badge {
        display: inline-block;
        background: linear-gradient(90deg, #22c55e, #16a34a);
        color: white; font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase;
        padding: 0.22rem 0.75rem; border-radius: 20px;
    }
    .app-title {
        font-size: 2.4rem; font-weight: 800;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0.3rem 0 0.1rem 0; text-align: center;
    }
    .app-tagline { font-size: 1rem; font-weight: 600; color: #333; text-align: center; margin: 0; }
    .app-sub     { font-size: 0.8rem; color: #888; text-align: center; margin-top: 0.1rem; }

    .control-box {
        background: #fafafa; border: 1px solid #eee;
        border-radius: 14px; padding: 1.2rem 1.4rem; margin: 1rem 0;
    }
    .step-label {
        font-size: 0.95rem; font-weight: 800; letter-spacing: 0.04em;
        color: #1a1a1a; margin-bottom: 0.15rem; margin-top: 0.6rem;
    }
    .step-num {
        display: inline-block;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        color: white; font-size: 0.75rem; font-weight: 900;
        width: 1.4rem; height: 1.4rem; line-height: 1.4rem;
        text-align: center; border-radius: 50%; margin-right: 0.4rem;
    }
    .prog-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.3rem; }
    .prog-chip {
        font-size: 0.75rem; background: #f0f0f0;
        border-radius: 20px; padding: 0.2rem 0.6rem; color: #444;
    }
</style>
""", unsafe_allow_html=True)

# ── Reset helper ──────────────────────────────────────────────────────────────
def reset_session():
    for k in ["messages", "display", "one_pager", "greeted", "pending_input"]:
        st.session_state.pop(k, None)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages"       not in st.session_state: st.session_state.messages       = [{"role": "system", "content": SYSTEM_PROMPT}]
if "display"        not in st.session_state: st.session_state.display        = []
if "one_pager"      not in st.session_state: st.session_state.one_pager      = None
if "greeted"        not in st.session_state: st.session_state.greeted        = False
if "pending_input"  not in st.session_state: st.session_state.pending_input  = None
if "api_key"        not in st.session_state: st.session_state.api_key        = ""

# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_one_pager(text):
    s, e = text.find("[ONE-PAGER-START]"), text.find("[ONE-PAGER-END]")
    if s != -1 and e != -1:
        return text[s + len("[ONE-PAGER-START]"):e].strip()

def clean_display(text):
    return text.replace("[ONE-PAGER-START]", "").replace("[ONE-PAGER-END]", "").strip()

CHOICE_TRIGGERS = [
    "which", "choose", "pick", "select", "option", "here are",
    "niche idea", "niche option", "which one", "resonate", "feel right",
    "which of these", "go with", "prefer"
]

def extract_numbered_options(text):
    lower = text.lower()
    # Only show buttons if Coach is presenting actual choices, not asking open questions
    if not any(t in lower for t in CHOICE_TRIGGERS):
        return []
    items = re.findall(r"^\s*\d+[\.\)]\s+(.+)", text, re.MULTILINE)
    return [i.strip() for i in items if len(i.strip()) > 3]

def detect_progress(display):
    coach = " ".join(m["content"] for m in display if m["role"] == "assistant")
    users = sum(1 for m in display if m["role"] == "user")
    return {
        "background": users >= 2,
        "niche":    any(w in coach.lower() for w in ["commit", "go with", "perfect niche", "chosen niche"]),
        "person":   "Person:"  in coach, "problem": "Problem:" in coach,
        "promise":  "Promise:" in coach, "plan":    "Plan:"    in coach,
        "product":  "Product:" in coach, "price":   "Price:"   in coach,
        "complete": st.session_state.one_pager is not None,
    }

def badge(done, active=False):
    return "✅" if done else ("🔄" if active else "⬜")

def stream_coach(client, messages):
    stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True, max_tokens=1024)
    for chunk in stream:
        yield chunk.choices[0].delta.content or ""

# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div style="text-align:center"><span class="free-badge">✦ 100% Free — No Cost, No Credit Card</span></div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">💰 MillionaireCoach</div>', unsafe_allow_html=True)
st.markdown('<p class="app-tagline">From $0 to your first $100k — step by step</p>', unsafe_allow_html=True)
st.markdown('<p class="app-sub">Find your niche · Build your offer · Get your first client</p>', unsafe_allow_html=True)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# CONTROL PANEL — single column, clear steps
# ═════════════════════════════════════════════════════════════════════════════
with st.container(border=True):

    # ── Step 1 ──
    st.markdown('<div class="step-label"><span class="step-num">1</span> Get Your Free API Key &amp; Enter It Below</div>', unsafe_allow_html=True)
    st.markdown("[→ Click here to get your free key at console.groq.com/keys](https://console.groq.com/keys)")

    with st.form("key_form", clear_on_submit=False):
        typed = st.text_input("Key", type="password", placeholder="Paste your gsk_... key here",
                              value=st.session_state.api_key, label_visibility="collapsed")
        if st.form_submit_button("✅ Submit API Key", use_container_width=True):
            if typed.strip():
                st.session_state.api_key = typed.strip()
                st.success("Key saved! Your coaching session will start below.")
            else:
                st.error("Please paste a valid Groq API key first.")

    st.divider()

    # ── Step 2 ──
    st.markdown('<div class="step-label"><span class="step-num">2</span> Start or Reset Your Coaching Session</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    if st.button("🔄  Start New Session", use_container_width=True, key="new_session"):
        reset_session()
        st.rerun()

    if st.session_state.one_pager:
        st.divider()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button("📄  Download Your One-Pager", data=st.session_state.one_pager,
                           file_name=f"my_offer_{ts}.txt", mime="text/plain",
                           use_container_width=True)

# Progress bar (compact chips, only shows after session starts)
p = detect_progress(st.session_state.display)
if any(p.values()):
    chips = []
    if p["background"]: chips.append("✅ Background")
    if p["niche"]:       chips.append("✅ Niche")
    for label, k in [("Person","person"),("Problem","problem"),("Promise","promise"),("Plan","plan"),("Product","product"),("Price","price")]:
        if p[k]: chips.append(f"✅ {label}")
    if chips:
        st.markdown('<div class="prog-row">' + "".join(f'<span class="prog-chip">{c}</span>' for c in chips) + '</div>', unsafe_allow_html=True)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# CHAT AREA
# ═════════════════════════════════════════════════════════════════════════════
api_key = st.session_state.api_key

if not api_key:
    st.info("👆 Paste your free Groq API key above and click **Submit API Key** to begin.")
    st.stop()

client = Groq(api_key=api_key)

# Chat history
for msg in st.session_state.display:
    with st.chat_message(msg["role"], avatar="💰" if msg["role"] == "assistant" else "🧑"):
        st.markdown(msg["content"])

# Auto-greet
if not st.session_state.greeted:
    with st.chat_message("assistant", avatar="💰"):
        try:
            response = st.write_stream(stream_coach(client, st.session_state.messages))
        except AuthenticationError:
            st.error("❌ Invalid API key. Please check and re-submit your Groq key above.")
            st.session_state.api_key = ""
            st.stop()
    clean = clean_display(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.display.append({"role": "assistant", "content": clean})
    st.session_state.greeted = True
    if op := extract_one_pager(response):
        st.session_state.one_pager = op
    st.rerun()

# Quick-reply buttons
if st.session_state.display and not st.session_state.one_pager:
    last = st.session_state.display[-1]
    if last["role"] == "assistant":
        options = extract_numbered_options(last["content"])
        if len(options) >= 2:
            st.markdown("**Quick replies:**")
            cols = st.columns(2)
            for i, opt in enumerate(options):
                with cols[i % 2]:
                    if st.button(f"{i+1}. {opt}", key=f"qr_{i}"):
                        st.session_state.pending_input = f"{i+1}. {opt}"

# Input
user_input = st.session_state.pending_input
st.session_state.pending_input = None
typed_msg = st.chat_input("Type your answer here, or click a quick reply above...")
if typed_msg:
    user_input = typed_msg

if user_input:
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)
    st.session_state.display.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant", avatar="💰"):
        try:
            response = st.write_stream(stream_coach(client, st.session_state.messages))
        except AuthenticationError:
            st.error("❌ Invalid API key. Please re-submit your Groq key above.")
            st.session_state.api_key = ""
            st.stop()

    clean = clean_display(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.display.append({"role": "assistant", "content": clean})
    if op := extract_one_pager(response):
        st.session_state.one_pager = op
    st.rerun()
