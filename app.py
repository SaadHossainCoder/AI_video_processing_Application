import sys
import os
import time
import tempfile
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import (
    extract_action_items,
    extract_key_decisions,
    extract_questions,
)
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()


class StreamlitLogRedirector:
    def __init__(self, code_placeholder):
        self.code_placeholder = code_placeholder
        self.all_text = ""
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def write(self, text):
        try:
            self._stdout.write(text)
        except Exception:
            pass
        if not text:
            return
        self.all_text += text
        clean_lines = []
        for raw_line in self.all_text.split("\n"):
            clean_line = raw_line.split("\r")[-1].strip()
            if clean_line:
                clean_lines.append(clean_line)
        display_text = "\n".join(clean_lines[-60:])
        try:
            self.code_placeholder.code(display_text, language="log")
        except Exception:
            pass

    def flush(self):
        try:
            self._stdout.flush()
        except Exception:
            pass

    def get_logs(self):
        clean_lines = []
        for raw_line in self.all_text.split("\n"):
            clean_line = raw_line.split("\r")[-1].strip()
            if clean_line:
                clean_lines.append(clean_line)
        return "\n".join(clean_lines)

    def __enter__(self):
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._stdout
        sys.stderr = self._stderr


def run_pipeline(source: str, translate: bool = False, update_progress=None) -> dict:
    print(f"Source: {source}")
    print(f"Translate: {translate}")
    print("Starting AI Video Assistant ⤵")

    if update_progress:
        update_progress(10, "📥 Downloading / processing input audio...")
    chunk = process_input(source)

    if update_progress:
        update_progress(35, "🎙️ Transcribing audio with Whisper...")
    transcript = transcribe_all(chunk, translate=translate)
    print(f"\nRaw transcription (first 300 characters):\n{transcript[:300]}...\n")

    if update_progress:
        update_progress(65, "🏷️ Generating video title and summary...")
    print("Generating title...")
    title = generate_title(transcript)
    print(f"Generated Title: {title}")

    print("Generating summary...")
    summary = summarize(transcript)

    if update_progress:
        update_progress(80, "📌 Extracting action items, decisions, and questions...")
    print("Extracting action items...")
    action_items = extract_action_items(transcript)
    print("Extracting key decisions...")
    decisions = extract_key_decisions(transcript)
    print("Extracting open questions...")
    questions = extract_questions(transcript)

    if update_progress:
        update_progress(92, "🧠 Indexing transcript into RAG vector database...")
    print("Building RAG vector store...")
    rag_chain = build_rag_chain(transcript)
    print("✓ Video analysis completed successfully!")

    if update_progress:
        update_progress(100, "🎉 Analysis completed successfully!")

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="VidSage AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# MODERN + CLASSIC STYLES
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

:root {
    --bg: #f7f7fb;
    --surface: #ffffff;
    --border: #e5e4ef;
    --text: #16151f;
    --muted: #6b6a7b;
    --accent: #6d4aff;
    --accent-hover: #5a3ae8;
    --accent-soft: #f3f0ff;
    --radius: 14px;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 32px;
    padding: 0 4px;
}

.brand-icon {
    width: 40px;
    height: 40px;
    border-radius: 11px;
    background: linear-gradient(135deg, #7c5cff, #5b3df0);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 4px 12px rgba(109, 74, 255, 0.25);
}

.brand-name {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 19px;
    letter-spacing: -0.5px;
}

.brand-subtitle {
    font-size: 11px;
    color: var(--muted);
}

/* Make sidebar buttons look clean */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 0.6rem 0.9rem !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--accent-soft) !important;
    color: var(--accent) !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--accent-soft) !important;
    color: var(--accent) !important;
    font-weight: 600 !important;
}

/* ---------- Hero ---------- */
.hero {
    padding: 12px 0 28px;
}

.eyebrow {
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.hero h1 {
    font-family: 'Manrope', sans-serif;
    font-size: clamp(32px, 4.2vw, 46px);
    font-weight: 800;
    letter-spacing: -1.6px;
    line-height: 1.15;
    margin: 0;
    color: var(--text);
}

.hero p {
    max-width: 560px;
    margin-top: 14px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
}

/* ---------- Section titles ---------- */
.section-title {
    font-family: 'Manrope', sans-serif;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: var(--text);
}

.section-subtitle {
    font-size: 13.5px;
    color: var(--muted);
    margin: 4px 0 18px;
}

/* ---------- Cards ---------- */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
}

.feature-item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
}

.feature-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.feature-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--accent-soft);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
}

.feature-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
}

.feature-desc {
    font-size: 13px;
    color: var(--muted);
    margin-top: 2px;
    line-height: 1.5;
}

/* ---------- Inputs & buttons ---------- */
.stTextInput input {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 11px !important;
    padding: 12px 14px !important;
    font-size: 14px !important;
    color: var(--text) !important;
}

.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(109, 74, 255, 0.12) !important;
}

/* File uploader – clean modern look */
[data-testid="stFileUploader"] {
    background: #faf9ff !important;
    border: 1.5px dashed #d4ccf5 !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;
}

[data-testid="stFileUploader"] section {
    padding: 8px 0 !important;
}

[data-testid="stFileUploader"] small {
    color: var(--muted) !important;
}

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    border-radius: 11px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    min-height: 44px !important;
    transition: all 0.15s ease !important;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c5cff, #5b3df0) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(109, 74, 255, 0.28) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(109, 74, 255, 0.35) !important;
    transform: translateY(-1px);
}

/* Status badge */
.status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 999px;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 48px 24px;
    background: white;
    border: 1.5px dashed #d4ccf5;
    border-radius: var(--radius);
}

.empty-icon {
    font-size: 36px;
    margin-bottom: 12px;
}

.empty-title {
    font-family: 'Manrope', sans-serif;
    font-weight: 700;
    font-size: 18px;
}

.empty-desc {
    font-size: 14px;
    color: var(--muted);
    max-width: 340px;
    margin: 8px auto 0;
    line-height: 1.6;
}

/* Chat bubbles */
.chat-user, .chat-assistant {
    border-radius: 14px;
    padding: 14px 16px;
    margin: 10px 0;
    line-height: 1.6;
}

.chat-user {
    background: var(--accent-soft);
    margin-left: 32px;
}

.chat-assistant {
    background: white;
    border: 1px solid var(--border);
    margin-right: 32px;
}

.chat-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 6px;
}

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
}

.metric-label {
    font-size: 12px;
    color: var(--muted);
}

.metric-value {
    font-family: 'Manrope', sans-serif;
    font-size: 22px;
    font-weight: 700;
    margin-top: 4px;
}

.footer {
    text-align: center;
    color: #9998a8;
    font-size: 12px;
    padding: 40px 0 20px;
}

/* Hide Streamlit default elements a bit cleaner */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# STATE
# --------------------------------------------------
if "result" not in st.session_state:
    st.session_state.result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "logs" not in st.session_state:
    st.session_state.logs = ""
if "page" not in st.session_state:
    st.session_state.page = "Home"


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand">
        <div class="brand-icon">✦</div>
        <div>
            <div class="brand-name">VidSage</div>
            <div class="brand-subtitle">AI video workspace</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("WORKSPACE")

    pages = [
        ("⌂", "Home"),
        ("✧", "Chat with Video"),
        ("▤", "Transcript"),
        ("◈", "Summary"),
        ("✓", "Action Items"),
        ("◇", "Key Decisions"),
        ("?", "Open Questions"),
        ("⚡", "Process Logs"),
    ]

    for icon, page in pages:
        if st.button(
            f"{icon}   {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if st.session_state.page == page else "secondary",
        ):
            st.session_state.page = page
            st.rerun()

    st.markdown("---")
    st.caption("CURRENT SESSION")

    if st.session_state.result:
        st.markdown('<span class="status">● Analysis ready</span>', unsafe_allow_html=True)
        st.caption(st.session_state.result.get("title", "Video analysis")[:60])
        if st.button("Clear workspace", use_container_width=True):
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.logs = ""
            st.session_state.page = "Home"
            st.rerun()
    else:
        st.caption("No video analyzed yet")


# --------------------------------------------------
# HERO
# --------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="eyebrow">✦ Your personal video assistant</div>
    <h1>Turn videos into <span style="color:#6d4aff;">insights.</span></h1>
    <p>Transform any video into summaries, transcripts, action items, key decisions, and interactive answers — all in one elegant workspace.</p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HOME
# --------------------------------------------------
if st.session_state.page == "Home":
    left, right = st.columns([1.3, 0.9], gap="large")

    with left:
        st.markdown('<div class="section-title">Start with your video</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Paste a YouTube link or upload a local file to begin.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**🔗 YouTube video**")
            source_url = st.text_input(
                "Video URL",
                placeholder="https://www.youtube.com/watch?v=...",
                label_visibility="collapsed",
            )

            st.markdown(
                "<div style='text-align:center; color:#9a99ad; font-size:11px; letter-spacing:0.8px; padding:16px 0 8px;'>— OR UPLOAD A FILE —</div>",
                unsafe_allow_html=True,
            )

            uploaded_file = st.file_uploader(
                "Upload video or audio",
                type=["mp4", "mkv", "mov", "avi", "mp3", "wav", "m4a", "webm"],
                label_visibility="collapsed",
            )

            translate = st.toggle("Translate transcription to English", value=False)

            if st.button("✦  Analyze video", type="primary", use_container_width=True):
                source = (source_url or "").strip().strip('"').strip("'")
                temporary_path = None

                if uploaded_file is not None:
                    suffix = Path(uploaded_file.name).suffix or ".mp4"
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(uploaded_file.getbuffer())
                            temporary_path = tmp.name
                        source = temporary_path
                    except Exception as e:
                        st.error(f"Could not prepare the uploaded file: {e}")
                        source = ""

                if not source:
                    st.warning("Please paste a video URL or upload a file.")
                else:
                    with st.container(border=True):
                        st.markdown("#### ⚡ Processing Progress")
                        status_box = st.status("🚀 Starting AI Video Assistant...", expanded=True)
                        with status_box:
                            prog_bar = st.progress(0, text="Initializing...")
                            log_placeholder = st.empty()
                            log_placeholder.code("Starting...\n", language="log")

                    def update_progress(percent, message):
                        prog_bar.progress(percent, text=message)
                        status_box.update(label=message, state="running")

                    redirector = None
                    try:
                        with StreamlitLogRedirector(log_placeholder) as redirector:
                            result = run_pipeline(source, translate=translate, update_progress=update_progress)

                        st.session_state.result = result
                        st.session_state.logs = redirector.get_logs()
                        st.session_state.chat_history = []

                        status_box.update(label="🎉 Analysis complete!", state="complete", expanded=False)
                        time.sleep(0.9)
                        st.session_state.page = "Summary"
                        st.rerun()

                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        if redirector:
                            st.session_state.logs = redirector.get_logs()
                    finally:
                        if temporary_path and os.path.exists(temporary_path):
                            try:
                                os.remove(temporary_path)
                            except OSError:
                                pass

    with right:
        st.markdown('<div class="section-title">Your AI workspace</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Everything stays organized in one place.</div>', unsafe_allow_html=True)

        with st.container(border=True):
            features = [
                ("📝", "Smart summary", "Grasp the main ideas in seconds."),
                ("✓", "Action items", "Surface tasks and next steps automatically."),
                ("◇", "Key decisions", "Keep important decisions clearly listed."),
                ("💬", "Chat with video", "Ask anything about the content."),
            ]
            for icon, title, desc in features:
                st.markdown(f"""
                <div class="feature-item">
                    <div class="feature-icon">{icon}</div>
                    <div>
                        <div class="feature-title">{title}</div>
                        <div class="feature-desc">{desc}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if not st.session_state.result:
            st.caption("01  Add a video  →  02  Analyze  →  03  Explore insights")


# --------------------------------------------------
# RESULTS
# --------------------------------------------------
result = st.session_state.result

if result is not None and st.session_state.page != "Home":
    st.markdown('<span class="status">● Analysis complete</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title" style="margin-top:14px;">{result.get("title", "Your video insights")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Explore every part of the analysis.</div>', unsafe_allow_html=True)

    if st.session_state.page == "Summary":
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Transcript</div>
                <div class="metric-value">{len(result.get("transcript", "")):,}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">Summary</div>
                <div class="metric-value">Ready</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            items = result.get("action_items", [])
            count = len(items) if isinstance(items, (list, tuple)) else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Action items</div>
                <div class="metric-value">{count}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            decisions = result.get("key_decisions", [])
            count = len(decisions) if isinstance(decisions, (list, tuple)) else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Key decisions</div>
                <div class="metric-value">{count}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown('<div class="section-title">Video summary</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write(result.get("summary", ""))
        st.download_button("↓ Download summary", data=str(result.get("summary", "")), file_name="summary.txt")

        t1, t2, t3 = st.tabs(["✓ Action Items", "◇ Key Decisions", "? Open Questions"])
        with t1:
            st.write(result.get("action_items", []))
        with t2:
            st.write(result.get("key_decisions", []))
        with t3:
            st.write(result.get("open_questions", []))

        with st.expander("📜 Processing Logs"):
            st.code(st.session_state.get("logs", "No logs"), language="log")

    elif st.session_state.page == "Process Logs":
        st.markdown('<div class="section-title">⚡ Processing Logs</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.code(st.session_state.get("logs", "No logs yet."), language="log")
        st.download_button("↓ Download logs", data=st.session_state.get("logs", ""), file_name="logs.txt")

    elif st.session_state.page == "Transcript":
        st.markdown('<div class="section-title">Full transcript</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.write(result.get("transcript", ""))
        st.download_button("↓ Download transcript", data=str(result.get("transcript", "")), file_name="transcript.txt")

    elif st.session_state.page == "Action Items":
        st.markdown('<div class="section-title">Action items</div>', unsafe_allow_html=True)
        st.write(result.get("action_items", []))

    elif st.session_state.page == "Key Decisions":
        st.markdown('<div class="section-title">Key decisions</div>', unsafe_allow_html=True)
        st.write(result.get("key_decisions", []))

    elif st.session_state.page == "Open Questions":
        st.markdown('<div class="section-title">Open questions</div>', unsafe_allow_html=True)
        st.write(result.get("open_questions", []))

    elif st.session_state.page == "Chat with Video":
        chat_col, info_col = st.columns([1.6, 0.85], gap="large")
        with chat_col:
            st.markdown('<div class="section-title">Chat with your video</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-subtitle">Ask anything about the content.</div>', unsafe_allow_html=True)

            with st.container(border=True):
                if not st.session_state.chat_history:
                    st.markdown("""
                    <div class="empty-state">
                        <div class="empty-icon">💬</div>
                        <div class="empty-title">Start a conversation</div>
                        <div class="empty-desc">Ask about takeaways, decisions, or any detail in the video.</div>
                    </div>
                    """, unsafe_allow_html=True)

                for msg in st.session_state.chat_history:
                    cls = "chat-user" if msg["role"] == "user" else "chat-assistant"
                    label = "You" if msg["role"] == "user" else "VidSage"
                    st.markdown(f'<div class="{cls}"><div class="chat-label">{label}</div>{msg["content"]}</div>', unsafe_allow_html=True)

            with st.form("chat_form", clear_on_submit=True):
                q = st.text_input("Ask a question", placeholder="What are the main takeaways?", label_visibility="collapsed")
                if st.form_submit_button("Send ↑", type="primary", use_container_width=True) and q.strip():
                    st.session_state.chat_history.append({"role": "user", "content": q.strip()})
                    try:
                        with st.spinner("Thinking..."):
                            ans = ask_question(result["rag_chain"], q.strip())
                        st.session_state.chat_history.append({"role": "assistant", "content": str(ans)})
                    except Exception as e:
                        st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
                    st.rerun()

        with info_col:
            with st.container(border=True):
                st.markdown("**Suggested questions**")
                for s in ["What are the main takeaways?", "What decisions were made?", "What action items were discussed?"]:
                    if st.button(s, key=f"sug_{s}", use_container_width=True):
                        st.session_state.chat_history.append({"role": "user", "content": s})
                        try:
                            with st.spinner("Thinking..."):
                                ans = ask_question(result["rag_chain"], s)
                            st.session_state.chat_history.append({"role": "assistant", "content": str(ans)})
                        except Exception as e:
                            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
                        st.rerun()
                if st.button("Clear chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()

elif st.session_state.page != "Home":
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">🎬</div>
        <div class="empty-title">Your workspace is waiting</div>
        <div class="empty-desc">Go to Home and analyze a video to explore the results.</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown('<div class="footer">VidSage AI · Turn video into understanding</div>', unsafe_allow_html=True)