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
    """Redirects stdout and stderr to both the original console and a Streamlit UI component in real-time."""

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

        # Clean carriage returns so tqdm/download bars display the latest state cleanly
        clean_lines = []
        for raw_line in self.all_text.split("\n"):
            clean_line = raw_line.split("\r")[-1].strip()
            if clean_line:
                clean_lines.append(clean_line)

        # Keep the latest 60 lines for snappy live browser rendering
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


# --------------------------------------------------
# PIPELINE WITH LIVE PROGRESS LOGGING
# --------------------------------------------------
def run_pipeline(source: str, translate: bool = False, update_progress=None) -> dict:
    print(f"Enter YouTube URL or local file path (⚠️ Only English video ⚠️): {source}")
    print(f"Translate transcription: {translate}")
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
# PAGE CONFIG + GLOBAL STYLES
# --------------------------------------------------
st.set_page_config(
    page_title="VidSage AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Manrope:wght@500;600;700;800&display=swap');

:root {
    --bg: #f6f5fb;
    --surface: #ffffff;
    --border: #e8e6f2;
    --text: #1e1d2f;
    --muted: #6e6d82;
    --accent: #6b4ef6;
    --accent-soft: #f0edff;
    --accent-border: #d9d0ff;
    --radius: 16px;
    --shadow: 0 4px 24px rgba(30, 29, 47, 0.04);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface);
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div:first-child {
    padding: 1.4rem 1rem 2rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 28px;
}

.brand-icon {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    background: linear-gradient(145deg, #8b6fff, #5a3de8);
    color: white;
    font-size: 20px;
    box-shadow: 0 4px 12px rgba(107, 78, 246, 0.25);
}

.brand-name {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 20px;
    letter-spacing: -0.6px;
    color: var(--text);
}

.brand-subtitle {
    color: var(--muted);
    font-size: 11px;
    margin-top: 1px;
}

/* Hero */
.hero {
    padding: 8px 0 28px;
}

.eyebrow {
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.6px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.hero h1 {
    font-family: 'Manrope', sans-serif;
    font-size: clamp(30px, 4vw, 44px);
    font-weight: 800;
    letter-spacing: -1.8px;
    line-height: 1.15;
    color: var(--text);
    margin: 0;
}

.hero p {
    max-width: 620px;
    margin-top: 12px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.7;
}

/* Sections */
.section-title {
    font-family: 'Manrope', sans-serif;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.4px;
    color: var(--text);
}

.section-subtitle {
    font-size: 13px;
    color: var(--muted);
    margin: 4px 0 18px;
}

/* Cards & panels */
.panel, .metric-card, .feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
}

.metric-card {
    padding: 18px;
    min-height: 100px;
}

.metric-icon {
    font-size: 18px;
    margin-bottom: 8px;
}

.metric-label {
    font-size: 11px;
    color: var(--muted);
    font-weight: 500;
}

.metric-value {
    font-family: 'Manrope', sans-serif;
    font-size: 22px;
    font-weight: 800;
    margin-top: 3px;
    color: var(--text);
}

.feature-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
}

.feature-description {
    font-size: 12.5px;
    color: var(--muted);
    line-height: 1.65;
    margin-top: 4px;
}

/* Status badge */
.status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--accent-soft);
    color: var(--accent);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    min-height: 42px;
    border-radius: 11px !important;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.18s ease;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7b5cff, #5a3de8) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(107, 78, 246, 0.28);
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(107, 78, 246, 0.35);
    transform: translateY(-1px);
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--accent) !important;
}

/* Inputs */
.stTextInput input {
    border-radius: 11px !important;
    border: 1px solid var(--border) !important;
}

.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(107, 78, 246, 0.12) !important;
}

/* File uploader – cleaner “preview” feel */
[data-testid="stFileUploader"] {
    background: #faf9ff;
    border: 1.5px dashed var(--accent-border);
    border-radius: 14px;
    padding: 14px 16px;
}

[data-testid="stFileUploader"] section {
    padding: 0;
}

[data-testid="stFileUploader"] label {
    font-size: 13px !important;
}

/* Chat bubbles */
.chat-user, .chat-assistant {
    border-radius: 14px;
    padding: 14px 16px;
    margin: 10px 0;
    line-height: 1.65;
    overflow-wrap: anywhere;
}

.chat-user {
    background: var(--accent-soft);
    border: 1px solid var(--accent-border);
    margin-left: 28px;
}

.chat-assistant {
    background: var(--surface);
    border: 1px solid var(--border);
    margin-right: 28px;
    box-shadow: var(--shadow);
}

.chat-label {
    color: var(--accent);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    background: var(--surface);
    border: 1.5px dashed var(--accent-border);
    border-radius: var(--radius);
}

.empty-icon {
    font-size: 36px;
    margin-bottom: 12px;
}

.empty-title {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 18px;
    color: var(--text);
}

.empty-description {
    font-size: 13.5px;
    color: var(--muted);
    line-height: 1.7;
    max-width: 380px;
    margin: 8px auto 0;
}

/* Footer */
.footer {
    text-align: center;
    color: #9a99ad;
    font-size: 12px;
    padding: 36px 0 16px;
}

hr {
    border-color: var(--border) !important;
}

/* Streamlit containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--radius) !important;
    border-color: var(--border) !important;
    box-shadow: var(--shadow);
}

@media (max-width: 768px) {
    .hero h1 {
        font-size: 28px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
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
    st.markdown(
        """
        <div class="brand">
            <div class="brand-icon">✦</div>
            <div>
                <div class="brand-name">VidSage</div>
                <div class="brand-subtitle">AI video workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("WORKSPACE")

    nav_items = [
        ("⌂", "Home"),
        ("✧", "Chat with Video"),
        ("▤", "Transcript"),
        ("◈", "Summary"),
        ("✓", "Action Items"),
        ("◇", "Key Decisions"),
        ("?", "Open Questions"),
        ("⚡", "Process Logs"),
    ]

    for icon, page in nav_items:
        is_active = st.session_state.page == page
        if st.button(
            f"{icon}   {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = page
            st.rerun()

    st.markdown("---")
    st.caption("CURRENT SESSION")

    if st.session_state.result:
        st.markdown(
            '<span class="status">● ANALYSIS READY</span>',
            unsafe_allow_html=True,
        )
        st.caption(st.session_state.result.get("title", "Video analysis"))

        if st.button("Clear workspace", use_container_width=True):
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.logs = ""
            st.session_state.page = "Home"
            st.rerun()
    else:
        st.caption("No video analyzed yet.")


# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">✦ Your personal video assistant</div>
        <h1>Turn videos into <span style="color:#6b4ef6;">insights.</span></h1>
        <p>Transform any video into summaries, transcripts, action items,
        key decisions, and interactive answers — all in one elegant workspace.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------
if st.session_state.page == "Home":
    left, right = st.columns([1.25, 0.85], gap="large")

    with left:
        st.markdown(
            '<div class="section-title">Start with your video</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">Paste a YouTube link or upload a local file to begin.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("##### 🔗 YouTube video")
            source_url = st.text_input(
                "Video URL",
                placeholder="https://www.youtube.com/watch?v=...",
                label_visibility="collapsed",
            )

            st.markdown(
                "<div style='text-align:center;color:#9a99ad;font-size:11px;"
                "letter-spacing:1px;padding:14px 0 6px;'>— OR UPLOAD A FILE —</div>",
                unsafe_allow_html=True,
            )

            uploaded_file = st.file_uploader(
                "Upload video or audio",
                type=["mp4", "mkv", "mov", "avi", "mp3", "wav", "m4a", "webm"],
                label_visibility="collapsed",
            )

            translate = st.toggle("Translate transcription to English", value=False)

            if st.button(
                "✦  Analyze video",
                type="primary",
                use_container_width=True,
            ):
                source = (source_url or "").strip().strip('"').strip("'")
                temporary_path = None

                if uploaded_file is not None:
                    suffix = Path(uploaded_file.name).suffix or ".mp4"
                    try:
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix
                        ) as temp_file:
                            temp_file.write(uploaded_file.getbuffer())
                            temporary_path = temp_file.name
                        source = temporary_path
                    except Exception as error:
                        st.error(f"Could not prepare the uploaded file: {error}")
                        source = ""

                if not source:
                    st.warning("Please paste a video URL or upload a file.")
                else:
                    progress_container = st.container(border=True)
                    with progress_container:
                        st.markdown("#### ⚡ Processing Progress & Logs")
                        status_box = st.status(
                            "🚀 Starting AI Video Assistant...", expanded=True
                        )
                        with status_box:
                            prog_bar = st.progress(0, text="Initializing pipeline...")
                            log_placeholder = st.empty()
                            log_placeholder.code(
                                "Starting AI Video Assistant ⤵\nWaiting for first step...",
                                language="log",
                            )

                    def update_progress(percent, message):
                        prog_bar.progress(percent, text=message)
                        status_box.update(label=message, state="running")

                    redirector = None
                    try:
                        with StreamlitLogRedirector(log_placeholder) as redirector:
                            result = run_pipeline(
                                source,
                                translate=translate,
                                update_progress=update_progress,
                            )

                        st.session_state.result = result
                        st.session_state.logs = redirector.get_logs()
                        st.session_state.chat_history = []

                        status_box.update(
                            label="🎉 Analysis completed! Opening Summary…",
                            state="complete",
                            expanded=False,
                        )
                        time.sleep(1.0)
                        st.session_state.page = "Summary"
                        st.rerun()

                    except Exception as error:
                        st.error(f"Video analysis failed: {error}")
                        if redirector is not None:
                            st.session_state.logs = redirector.get_logs()

                    finally:
                        if temporary_path and os.path.exists(temporary_path):
                            try:
                                os.remove(temporary_path)
                            except OSError:
                                pass

    with right:
        st.markdown(
            '<div class="section-title">Your AI workspace</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">Everything stays organized in one place.</div>',
            unsafe_allow_html=True,
        )

        features = [
            ("📝", "Smart summary", "Grasp the main ideas in seconds."),
            ("✓", "Action items", "Surface tasks and next steps automatically."),
            ("◇", "Key decisions", "Keep important decisions clearly listed."),
            ("💬", "Chat with video", "Ask anything about the content."),
        ]

        for icon, title, description in features:
            with st.container(border=True):
                st.markdown(
                    f'<div class="feature-title">{icon}  {title}</div>'
                    f'<div class="feature-description">{description}</div>',
                    unsafe_allow_html=True,
                )

        if not st.session_state.result:
            st.caption("01  Add a video  →  02  Analyze  →  03  Explore insights")


# --------------------------------------------------
# RESULTS PAGES
# --------------------------------------------------
result = st.session_state.result

if result is not None and st.session_state.page != "Home":
    st.markdown(
        '<span class="status">● ANALYSIS COMPLETE</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="section-title" style="margin-top:14px;">'
        f'{result.get("title", "Your video insights")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Explore every part of the analysis.</div>',
        unsafe_allow_html=True,
    )

    # ---------- Summary ----------
    if st.session_state.page == "Summary":
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">📝</div>'
                f'<div class="metric-label">Transcript chars</div>'
                f'<div class="metric-value">{len(result.get("transcript", "")):,}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">✦</div>'
                f'<div class="metric-label">Summary</div>'
                f'<div class="metric-value">Ready</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        with col3:
            items = result.get("action_items", [])
            count = len(items) if isinstance(items, (list, tuple)) else 0
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">✓</div>'
                f'<div class="metric-label">Action items</div>'
                f'<div class="metric-value">{count}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        with col4:
            decisions = result.get("key_decisions", [])
            count = len(decisions) if isinstance(decisions, (list, tuple)) else 0
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-icon">◇</div>'
                f'<div class="metric-label">Key decisions</div>'
                f'<div class="metric-value">{count}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("")
        st.markdown(
            '<div class="section-title">Video summary</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">The main ideas and takeaways.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.write(result.get("summary", ""))

        st.download_button(
            "↓ Download summary",
            data=str(result.get("summary", "")),
            file_name="video_summary.txt",
            mime="text/plain",
        )

        tab1, tab2, tab3 = st.tabs(
            ["✓ Action Items", "◇ Key Decisions", "? Open Questions"]
        )

        with tab1:
            st.write(result.get("action_items", []))
            st.download_button(
                "Download action items",
                data=str(result.get("action_items", [])),
                file_name="action_items.txt",
            )

        with tab2:
            st.write(result.get("key_decisions", []))
            st.download_button(
                "Download key decisions",
                data=str(result.get("key_decisions", [])),
                file_name="key_decisions.txt",
            )

        with tab3:
            st.write(result.get("open_questions", []))
            st.download_button(
                "Download open questions",
                data=str(result.get("open_questions", [])),
                file_name="open_questions.txt",
            )

        with st.expander("📜 Processing Logs & Execution Details", expanded=False):
            st.code(
                st.session_state.get("logs", "No logs recorded."),
                language="log",
            )

    # ---------- Process Logs ----------
    elif st.session_state.page == "Process Logs":
        st.markdown(
            '<div class="section-title">⚡ Execution & Processing Logs</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">Terminal output, model events, and transcription progress.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.code(
                st.session_state.get(
                    "logs",
                    "No processing logs recorded yet. Analyze a video from the Home page.",
                ),
                language="log",
            )

        st.download_button(
            "↓ Download logs",
            data=st.session_state.get("logs", ""),
            file_name="processing_logs.txt",
            mime="text/plain",
        )

    # ---------- Transcript ----------
    elif st.session_state.page == "Transcript":
        st.markdown(
            '<div class="section-title">Full transcript</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">Read or download the complete transcription.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.write(result.get("transcript", ""))

        st.download_button(
            "↓ Download transcript",
            data=str(result.get("transcript", "")),
            file_name="transcript.txt",
            mime="text/plain",
        )

    # ---------- Action Items ----------
    elif st.session_state.page == "Action Items":
        st.markdown(
            '<div class="section-title">Action items</div>',
            unsafe_allow_html=True,
        )
        st.write(result.get("action_items", []))
        st.download_button(
            "↓ Download",
            data=str(result.get("action_items", [])),
            file_name="action_items.txt",
        )

    # ---------- Key Decisions ----------
    elif st.session_state.page == "Key Decisions":
        st.markdown(
            '<div class="section-title">Key decisions</div>',
            unsafe_allow_html=True,
        )
        st.write(result.get("key_decisions", []))
        st.download_button(
            "↓ Download",
            data=str(result.get("key_decisions", [])),
            file_name="key_decisions.txt",
        )

    # ---------- Open Questions ----------
    elif st.session_state.page == "Open Questions":
        st.markdown(
            '<div class="section-title">Open questions</div>',
            unsafe_allow_html=True,
        )
        st.write(result.get("open_questions", []))
        st.download_button(
            "↓ Download",
            data=str(result.get("open_questions", [])),
            file_name="open_questions.txt",
        )

    # ---------- Chat with Video ----------
    elif st.session_state.page == "Chat with Video":
        chat_col, info_col = st.columns([1.55, 0.85], gap="large")

        with chat_col:
            st.markdown(
                '<div class="section-title">Chat with your video</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="section-subtitle">Ask anything about the analyzed content.</div>',
                unsafe_allow_html=True,
            )

            with st.container(border=True):
                if not st.session_state.chat_history:
                    st.markdown(
                        """
                        <div class="empty-state">
                            <div class="empty-icon">💬</div>
                            <div class="empty-title">Start a conversation</div>
                            <div class="empty-description">
                                Ask about the main takeaways, important details,
                                or decisions in your video.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                for message in st.session_state.chat_history:
                    role_class = (
                        "chat-user" if message["role"] == "user" else "chat-assistant"
                    )
                    role_label = (
                        "You" if message["role"] == "user" else "VidSage AI"
                    )
                    st.markdown(
                        f'<div class="{role_class}">'
                        f'<div class="chat-label">{role_label}</div>'
                        f'{message["content"]}</div>',
                        unsafe_allow_html=True,
                    )

            with st.form("chat_form", clear_on_submit=True):
                question = st.text_input(
                    "Ask a question",
                    placeholder="What are the main takeaways?",
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "Send question  ↑",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and question.strip():
                st.session_state.chat_history.append(
                    {"role": "user", "content": question.strip()}
                )
                try:
                    with st.spinner("Finding an answer..."):
                        answer = ask_question(
                            result["rag_chain"], question.strip()
                        )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": str(answer)}
                    )
                except Exception as error:
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": f"Could not generate an answer: {error}",
                        }
                    )
                st.rerun()

        with info_col:
            with st.container(border=True):
                st.markdown("### ✦ Video context")
                st.caption("Questions are answered using your RAG pipeline.")
                st.markdown("---")
                st.markdown("**Suggested questions**")

                for suggestion in [
                    "What are the main takeaways?",
                    "What decisions were made?",
                    "What action items were discussed?",
                ]:
                    if st.button(
                        suggestion,
                        key=f"suggestion_{suggestion}",
                        use_container_width=True,
                    ):
                        st.session_state.chat_history.append(
                            {"role": "user", "content": suggestion}
                        )
                        try:
                            with st.spinner("Finding an answer..."):
                                answer = ask_question(
                                    result["rag_chain"], suggestion
                                )
                            st.session_state.chat_history.append(
                                {"role": "assistant", "content": str(answer)}
                            )
                        except Exception as error:
                            st.session_state.chat_history.append(
                                {
                                    "role": "assistant",
                                    "content": f"Could not generate an answer: {error}",
                                }
                            )
                        st.rerun()

                if st.button("Clear chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()

# Empty state for other pages when no result
elif st.session_state.page != "Home":
    if st.session_state.page == "Process Logs":
        st.markdown(
            '<div class="section-title">⚡ Execution & Processing Logs</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-subtitle">Real-time terminal output and progress.</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.code(
                st.session_state.get("logs")
                or "No processing logs recorded yet. Analyze a video from the Home page.",
                language="log",
            )
        if st.session_state.get("logs"):
            st.download_button(
                "↓ Download logs",
                data=st.session_state.get("logs", ""),
                file_name="processing_logs.txt",
                mime="text/plain",
            )
    else:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">🎬</div>
                <div class="empty-title">Your workspace is waiting</div>
                <div class="empty-description">
                    Go to Home and analyze a video to explore your results.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown(
    """
    <div class="footer">
        VidSage AI · Turn video into understanding
    </div>
    """,
    unsafe_allow_html=True,
)


if __name__ == "__main__":
    import streamlit.runtime
    if not streamlit.runtime.exists():
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", __file__]
        sys.exit(stcli.main())