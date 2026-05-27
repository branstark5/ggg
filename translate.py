import streamlit as st
from google import genai
import concurrent.futures
import time

# 1. Page Config
st.set_page_config(page_title="Subtitle Translator", page_icon="🌿", layout="centered")

# 2. Upgraded Soft Green UI CSS
st.markdown("""
    <style>
    /* Soft Mint Green Background */
    .stApp { 
        background-color: #F0FDF4 !important; 
        color: #1e293b !important; 
    }
    header, footer {visibility: hidden;}
    
    /* Remove the default top padding */
    .block-container {
        padding-top: 2rem !important;
    }
    
    /* The Custom Dashboard Header */
    .dashboard-header {
        background: #ffffff;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 20px 25px;
        box-shadow: 0 4px 20px rgba(34, 197, 94, 0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #166534;
        margin: 0;
    }
    .status-badge {
        background: #dcfce7;
        color: #15803d;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #bbf7d0;
    }
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #22c55e;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #22c55e;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }
        100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    
    /* Crisp White Card for Controls */
    div[data-testid="stForm"], div[data-testid="stVerticalBlock"] > div:nth-of-type(2) {
        background: #ffffff !important; 
        border: 1px solid #bbf7d0 !important; 
        border-radius: 12px !important; 
        padding: 25px !important;
        box-shadow: 0 4px 20px rgba(34, 197, 94, 0.08) !important;
    }
    
    /* Force text to be dark readable slate */
    label, p, span, .st-markdown { 
        color: #334155 !important; 
    }
    
    /* Soft Green Action Button */
    .stButton > button {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important; 
        color: white !important; 
        font-weight: bold !important; 
        font-size: 1.05rem !important;
        width: 100% !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px !important;
        box-shadow: 0 4px 10px rgba(34, 197, 94, 0.25) !important;
        transition: all 0.3s ease !important;
        margin-top: 10px !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(34, 197, 94, 0.4) !important;
    }
    
    /* File Uploader tweaks */
    div[data-testid="stFileUploader"] {
        border: 2px dashed #86efac !important;
        background-color: #f8fafc !important;
        border-radius: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. The Dashboard Header
st.markdown("""
    <div class="dashboard-header">
        <div class="header-title">Burmese Subtitle Translator</div>
        <div class="status-badge">
            <span class="status-dot"></span> API Ready
        </div>
    </div>
""", unsafe_allow_html=True)

# 4. Settings Controls with Tooltips
api_key = st.text_input("API Key", type="password")

col1, col2, col3 = st.columns(3)
with col1:
    model_choice = st.selectbox(
        "AI Engine", 
        ["gemini-2.5-flash-lite", "gemini-3.5-flash"],
        help="2.5 Flash is cheaper and has higher free limits. 3.5 Flash is smarter but costs more."
    )
with col2:
    chunk_size = st.slider(
        "Lines per Request", 
        30, 150, 70,
        help="How many lines are translated at once. Set to 70-100 to save your daily request limits."
    )
with col3:
    parallel_workers = st.slider(
        "Parallel Threads", 
        1, 10, 5,
        help="How many chunks translate at the EXACT same time. Higher (5-10) is much faster, but requires a paid billing account."
    )

uploaded_file = st.file_uploader("Upload SRT", type=["srt"])

# -----------------------------------------
# The Parallel Worker Function
# -----------------------------------------
def translate_single_chunk(chunk_data):
    idx, chunk_text, api_token, model = chunk_data
    local_client = genai.Client(api_key=api_token)
    prompt = f"""You are a professional film localizer. Translate the dialogue text into natural, colloquial spoken Burmese (လူပြောစကား). 
    Strictly maintain the exact numbers, timeline codes, and formatting. Output only the translated SRT content.
    
    CONTENT TO TRANSLATE:
    {chunk_text}"""
    
    response = local_client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return idx, response.text.strip()

# -----------------------------------------
# Execution Logic
# -----------------------------------------
if st.button("Translate Subtitles") and uploaded_file and api_key:
    try:
        raw_content = uploaded_file.read().decode("utf-8")
        blocks = raw_content.replace("\r\n", "\n").strip().split("\n\n")
        
        chunk_packages = []
        for idx, i in enumerate(range(0, len(blocks), chunk_size)):
            chunk = blocks[i:i + chunk_size]
            chunk_packages.append((idx, "\n\n".join(chunk), api_key, model_choice))
            
        st.info(f"✨ File split into {len(chunk_packages)} sequence blocks. Processing...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        completed_results = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            futures = [executor.submit(translate_single_chunk, pkg) for pkg in chunk_packages]
            
            for count, future in enumerate(concurrent.futures.as_completed(futures)):
                completed_results.append(future.result())
                progress = (count + 1) / len(chunk_packages)
                progress_bar.progress(progress)
                status_text.caption(f"Processing... ({count + 1}/{len(chunk_packages)} blocks completed)")

        completed_results.sort(key=lambda x: x[0])
        final_output = [result[1] for result in completed_results]
        complete_srt = "\n\n".join(final_output)
        
        end_time = time.time()
        st.success(f"🎉 Translation complete in {round(end_time - start_time, 1)} seconds!")
        
        st.download_button(
            label="Download .SRT File",
            data=complete_srt,
            file_name="translated_burmese.srt",
            mime="text/plain"
        )
        
    except Exception as e:
        st.error(f"System Error: {str(e)}")