import streamlit as st
import anthropic
import json
import os
import re
import time

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MentorLab · EPIC Lab",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data
def load_mentors():
    with open("mentors.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_system_prompt(mentors_json: str):
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()
    return template.replace("{MENTORS_JSON}", mentors_json)

mentors       = load_mentors()
mentors_str   = json.dumps(mentors, ensure_ascii=False, indent=2)
SYSTEM_PROMPT = load_system_prompt(mentors_str)

# ─────────────────────────────────────────────
# ANTHROPIC CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("⚠️ ANTHROPIC_API_KEY not found.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)

client = get_client()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def score_bar_html(score: int) -> str:
    filled = round(score / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    color  = "#1B6B3A" if score >= 80 else "#2D5A3D" if score >= 65 else "#8B6914"
    return (
        f'<span style="font-family:monospace;font-size:0.8rem;color:{color}">'
        f'{bar} <b>{score}%</b></span>'
    )

def inject_scores(text: str) -> str:
    return re.sub(
        r'\[SCORE:(\d+)\]',
        lambda m: " " + score_bar_html(int(m.group(1))),
        text
    )

def parse_match_cards(text: str) -> list:
    cards   = []
    medals  = ['🥇', '🥈', '🥉']
    pattern = r'[🥇🥈🥉]\s*\*?\*?([^—\n]+?)\s*—\s*([^\[\n]+?)\s*\[SCORE:(\d+)\]'
    found   = re.findall(pattern, text)
    for i, (name, title, score) in enumerate(found[:3]):
        name_clean = name.strip().strip('*').strip()
        db = next((m for m in mentors if name_clean.lower() in m['name'].lower()), {})
        cards.append({
            'medal':         medals[i],
            'name':          name_clean,
            'title':         title.strip(),
            'score':         int(score),
            'industries':    db.get('industry', []),
            'expertise':     db.get('expertise', [])[:3],
            'availability':  db.get('availability', ''),
            'response_time': db.get('response_time', ''),
            'background':    db.get('background', ''),
        })
    return cards

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
DEFAULTS = {
    "messages":        [],
    "turn_count":      0,
    "matching_done":   False,
    "queued_input":    None,
    "refinement_mode": False,
    "mentor_cards":    [],
    "started":         False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;1,700&family=Source+Sans+3:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Sans 3', sans-serif !important;
    background-color: #EAE6DA !important;
}
.stApp { background-color: #EAE6DA !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 3rem 2rem 2rem !important; max-width: 680px !important; }

/* ── Landing ── */
.landing { text-align:center; padding:5rem 1rem 3rem; max-width:600px; margin:0 auto; }
.landing-title {
    font-family:'Playfair Display',serif !important;
    font-size:5rem; font-weight:800; color:#1B3A2D;
    line-height:1; margin:0 0 1.2rem; letter-spacing:-2px;
}
.landing-title em { font-style:italic; color:#2D6A4F; }
.landing-mission {
    font-family:'Playfair Display',serif !important;
    font-size:2rem; font-weight:700; color:#1B3A2D;
    line-height:1.2; margin:0 0 1rem; letter-spacing:-0.5px;
}
.landing-mission em { font-style:italic; color:#2D6A4F; }
.landing-sub {
    font-size:1rem; color:#4A6B5A; font-weight:300;
    margin:0 0 2rem; line-height:1.65;
}
.trust-bar { font-size:0.72rem; color:#7A9B8A; margin-top:1.8rem; letter-spacing:0.3px; }
.trust-bar b { color:#2D6A4F; }

/* ── App header ── */
.app-header { text-align:center; padding:1.5rem 0 0.5rem; }
.app-title {
    font-family:'Playfair Display',serif !important;
    font-size:1.8rem; font-weight:800; color:#1B3A2D; margin:0 0 0.1rem; letter-spacing:-0.3px;
}
.app-title em { font-style:italic; color:#2D6A4F; }
.app-sub    { font-size:0.82rem; color:#7A9B8A; margin:0 0 0.15rem; }
.app-byline { font-size:0.7rem; color:#A8BFB3; }

/* ── CTA button ── */
div[data-testid="stButton"] > button {
    background: #1B3A2D !important; color: #EAE6DA !important;
    border: none !important; border-radius: 50px !important;
    padding: 0.65rem 2.8rem !important; font-size: 1rem !important;
    font-weight: 600 !important; transition: all 0.2s !important;
}
div[data-testid="stButton"] > button:hover {
    background: #2D6A4F !important; transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(27,58,45,0.2) !important;
}

/* ── Progress pills ── */
.prog-row  { display:flex; justify-content:center; gap:0.4rem; margin-bottom:1.2rem; flex-wrap:wrap; }
.p-pill    { padding:0.22rem 0.85rem; border-radius:20px; font-size:0.7rem; font-weight:600; }
.p-active  { background:#1B3A2D; color:#EAE6DA; }
.p-done    { background:#2D6A4F; color:#EAE6DA; }
.p-pending { background:rgba(27,58,45,0.1); color:#7A9B8A; }

/* ── Chat bubbles ── */
.bubble-bot {
    background: #fff; border: 1px solid rgba(27,58,45,0.1);
    border-radius: 2px 16px 16px 16px; padding: 1rem 1.2rem; margin: 0.6rem 0;
    color: #1B3A2D; font-size: 0.93rem; line-height: 1.7;
    box-shadow: 0 1px 4px rgba(27,58,45,0.06);
}
.bubble-user {
    background: #1B3A2D; border-radius: 16px 2px 16px 16px;
    padding: 0.9rem 1.2rem; margin: 0.6rem 0;
    color: #D4EDE1; font-size: 0.93rem; line-height: 1.7;
}
.bubble-label {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.8px;
    text-transform: uppercase; margin-bottom: 0.4rem; opacity: 0.45;
}
.bubble-bot  .bubble-label { color: #1B3A2D; }
.bubble-user .bubble-label { color: #D4EDE1; }

/* ── Typing indicator ── */
.typing-bubble {
    background: #fff; border: 1px solid rgba(27,58,45,0.1);
    border-radius: 2px 16px 16px 16px; padding: 1rem 1.2rem; margin: 0.6rem 0;
    box-shadow: 0 1px 4px rgba(27,58,45,0.06); display: inline-block;
}
.typing-label {
    font-size:0.65rem; font-weight:600; letter-spacing:0.8px;
    text-transform:uppercase; opacity:0.45; margin-bottom:0.5rem; color:#1B3A2D;
}
.typing-dots { display:flex; gap:5px; align-items:center; height:18px; }
.typing-dots span {
    width:8px; height:8px; border-radius:50%; background:#2D6A4F;
    animation: tdot 1.2s infinite ease-in-out;
}
.typing-dots span:nth-child(2) { animation-delay:0.2s; }
.typing-dots span:nth-child(3) { animation-delay:0.4s; }
@keyframes tdot {
    0%,60%,100% { transform:translateY(0); opacity:0.35; }
    30%          { transform:translateY(-6px); opacity:1; }
}

/* ── Mentor cards ── */
.m-card {
    background:#fff; border:1px solid rgba(27,58,45,0.12); border-radius:14px;
    padding:1.1rem 1.3rem; margin-bottom:0.75rem;
    box-shadow:0 2px 8px rgba(27,58,45,0.06);
}
.m-name {
    font-family:'Playfair Display',serif !important;
    font-size:1.1rem; color:#1B3A2D; margin:0 0 0.15rem; font-weight:700;
}
.m-role  { font-size:0.78rem; color:#2D6A4F; font-weight:600; margin:0 0 0.4rem; }
.m-bg    { font-size:0.8rem; color:#4A6B5A; margin:0 0 0.55rem; line-height:1.5; }
.m-tag   {
    display:inline-block; background:#EAE6DA; color:#1B3A2D;
    border-radius:6px; padding:0.12rem 0.55rem;
    font-size:0.68rem; font-weight:600; margin:0.1rem 0.15rem 0.1rem 0;
}
.m-meta  { font-size:0.75rem; color:#7A9B8A; margin-top:0.55rem; display:flex; gap:1.2rem; }

/* ── Stage / refine buttons ── */
div[data-testid="stHorizontalBlock"] button {
    background: #fff !important; color: #1B3A2D !important;
    border: 1px solid rgba(27,58,45,0.25) !important; border-radius: 50px !important;
    font-size: 0.8rem !important; font-weight: 500 !important;
    white-space: nowrap !important; min-height: 42px !important;
    transition: all 0.15s !important;
}
div[data-testid="stHorizontalBlock"] button:hover {
    background: #1B3A2D !important; color: #EAE6DA !important;
    border-color: #1B3A2D !important;
}

/* ── Labels ── */
.section-label {
    text-align:center; color:#7A9B8A; font-size:0.7rem; font-weight:600;
    letter-spacing:1px; text-transform:uppercase; margin:1rem 0 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GREETING
# ─────────────────────────────────────────────
GREETING = (
    "Ok — let's go 👀\n\n"
    "I'm **MentorLab**, EPIC Lab's AI matching assistant.\n"
    "Tell me about your startup:\n"
    "- What **industry** are you in?\n"
    "- What **stage** are you at? *(Idea / Pre-seed / Seed / Series A)*\n"
    "- In one sentence: what does your product do?\n\n"
    "Or select your stage below:"
)
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": GREETING})

# ─────────────────────────────────────────────
# LANDING PAGE
# ─────────────────────────────────────────────
if not st.session_state.started:
    st.markdown(f"""
    <div class="landing">
        <p class="landing-title"><em>Mentor</em>Lab</p>
        <p class="landing-mission">
            Find the <em>right</em> mentor<br>for your startup.
        </p>
        <p class="landing-sub">
            Answer 3 questions. Our AI analyzes compatibility<br>
            and connects you with the best EPIC Lab mentors<br>
            for your stage and challenges.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        if st.button("Get Started →", use_container_width=True):
            st.session_state.started = True
            st.rerun()

    st.markdown(
        f'<p class="trust-bar" style="text-align:center">'
        f'<b>{len(mentors)} mentors</b> available · '
        f'Built by <b>Andre Butrón</b> · EPIC Lab · ITAM · MAD Fellows 2026'
        f'</p>',
        unsafe_allow_html=True
    )
    st.stop()

# ─────────────────────────────────────────────
# APP HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="app-title"><em>Mentor</em>Lab</p>
    <p class="app-sub">EPIC Lab · AI-powered mentor matching</p>
    <p class="app-byline">Built by Andre Butrón · MAD Fellows 2026</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROGRESS PILLS
# ─────────────────────────────────────────────
def pcls(n):
    if st.session_state.matching_done:   return "p-done"
    if n < st.session_state.turn_count:  return "p-done"
    if n == st.session_state.turn_count: return "p-active"
    return "p-pending"

pills = "".join(
    f'<span class="p-pill {pcls(i)}">{lbl}</span>'
    for i, lbl in enumerate(["1 · Startup", "2 · Challenge", "3 · Style", "🎯 Match"])
)
st.markdown(f'<div class="prog-row">{pills}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CHAT MESSAGES
# ─────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.markdown(
            f'<div class="bubble-bot">'
            f'<div class="bubble-label">🚀 MentorLab</div>'
            f'{inject_scores(msg["content"])}'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="bubble-user">'
            f'<div class="bubble-label">You</div>'
            f'{msg["content"]}'
            f'</div>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# MENTOR CARDS
# ─────────────────────────────────────────────
if st.session_state.mentor_cards:
    st.markdown('<p class="section-label">Your Top 3</p>', unsafe_allow_html=True)
    for c in st.session_state.mentor_cards:
        score  = c['score']
        filled = round(score / 10)
        bar    = "█" * filled + "░" * (10 - filled)
        color  = "#1B6B3A" if score >= 80 else "#2D5A3D" if score >= 65 else "#8B6914"
        tags   = "".join(f'<span class="m-tag">{t}</span>' for t in c['industries'] + c['expertise'])
        st.markdown(
            f'<div class="m-card">'
            f'  <div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'    <p class="m-name">{c["medal"]} {c["name"]}</p>'
            f'    <span style="font-family:monospace;font-size:0.78rem;color:{color};text-align:right">'
            f'      {bar}<br><b>{score}%</b></span>'
            f'  </div>'
            f'  <p class="m-role">{c["title"]}</p>'
            f'  <p class="m-bg">{c["background"]}</p>'
            f'  <div>{tags}</div>'
            f'  <div class="m-meta"><span>📅 {c["availability"]}</span><span>⏱ {c["response_time"]}</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# STAGE QUICK-SELECT (turn 0)
# ─────────────────────────────────────────────
if st.session_state.turn_count == 0 and not st.session_state.matching_done:
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    for col, (lbl, val) in zip([c1,c2,c3,c4], [
        ("💡 Idea","Idea"), ("🌱 Pre-seed","Pre-seed"),
        ("🚀 Seed","Seed"), ("📈 Series A","Series A")
    ]):
        if col.button(lbl, key=f"s_{val}"):
            st.session_state.queued_input = (
                f"My startup is at {val} stage. Please ask me what you need to know."
            )
            st.rerun()
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# REFINE / RESET (after match)
# ─────────────────────────────────────────────
if st.session_state.matching_done:
    st.markdown('<p class="section-label">Refine results</p>', unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    for col, (lbl, prompt) in zip([r1,r2,r3], [
        ("🔧 More technical",  "I want a more technical mentor, focused on product or engineering."),
        ("🤝 Hands-on",        "I want a more hands-on mentor, working with me week to week."),
        ("💰 Fundraising",     "I want to prioritize a mentor with expertise in fundraising and VCs."),
    ]):
        if col.button(lbl, key=f"rf_{lbl}"):
            st.session_state.queued_input    = prompt
            st.session_state.matching_done   = False
            st.session_state.refinement_mode = True
            st.rerun()
    if r4.button("🔄 New search", key="new"):
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        st.session_state.started = True
        st.rerun()

# ─────────────────────────────────────────────
# CHAT INPUT
# ─────────────────────────────────────────────
placeholder_map = {
    0: "Tell me about your startup: industry, stage and what it does...",
    1: "What is your biggest challenge and goal in the next few months?",
    2: "Do you prefer a hands-on or strategic mentor? How many sessions per month?",
}
if st.session_state.refinement_mode:
    ph = "Type to refine the match..."
elif st.session_state.matching_done:
    ph = "Match complete — use 'New search' to start over."
else:
    ph = placeholder_map.get(st.session_state.turn_count, "Type your response...")

typed = st.chat_input(
    ph,
    disabled=(st.session_state.matching_done and not st.session_state.refinement_mode)
)

user_input = typed or st.session_state.queued_input
if st.session_state.queued_input:
    st.session_state.queued_input = None

# ─────────────────────────────────────────────
# PROCESS
# ─────────────────────────────────────────────
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.turn_count += 1

    api_msgs = [
        m for m in st.session_state.messages
        if not (m["role"] == "assistant" and m["content"] == GREETING)
    ]

    is_matching = st.session_state.turn_count >= 3 or st.session_state.refinement_mode

    loading = st.empty()
    if is_matching:
        for step_msg, delay in [
            ("🔍 Analyzing your profile...",       0.5),
            ("🧠 Comparing 9 mentors...",          0.7),
            ("⚖️  Evaluating compatibility...",    0.5),
            ("✅ Top match found",                  0.3),
        ]:
            loading.markdown(
                f'<div class="typing-bubble">'
                f'<div class="typing-label">🚀 MentorLab</div>'
                f'<span style="font-size:0.85rem;color:#4A6B5A">{step_msg}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            time.sleep(delay)
    else:
        loading.markdown(
            '<div class="typing-bubble">'
            '<div class="typing-label">🚀 MentorLab</div>'
            '<div class="typing-dots"><span></span><span></span><span></span></div>'
            '</div>',
            unsafe_allow_html=True
        )

    # Retry up to 3 times on overload
    max_retries = 3
    raw = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1800,
                system=SYSTEM_PROMPT,
                messages=api_msgs,
            )
            raw = response.content[0].text
            break
        except Exception as e:
            if attempt < max_retries - 1:
                loading.markdown(
                    f'<div class="typing-bubble">'
                    f'<div class="typing-label">🚀 MentorLab</div>'
                    f'<span style="font-size:0.85rem;color:#4A6B5A">Server busy, retrying... ({attempt + 2}/{max_retries})</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                time.sleep(3)
            else:
                loading.empty()
                st.error("The AI server is temporarily overloaded. Please wait 30 seconds and try again.")
                st.stop()

    if raw is None:
        st.stop()
    loading.empty()
    st.session_state.messages.append({"role": "assistant", "content": raw})

    if "🥇" in raw and "🥈" in raw and "🥉" in raw:
        cards = parse_match_cards(raw)
        if cards:
            st.session_state.mentor_cards = cards
        st.session_state.matching_done   = True
        st.session_state.refinement_mode = False
        st.balloons()

    st.rerun()
