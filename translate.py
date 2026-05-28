import streamlit as st
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai

# 1. Page Configuration & Layout
st.set_page_config(
    page_title="Burmese Subtitle Translator", 
    page_icon="🌿", 
    layout="wide"
)

# Custom injection for a clean interface design
st.markdown("""
    <style>
    .main .block-container { max-width: 1100px; padding-top: 2rem; }
    div.stButton > button:first-child { background-color: #10b981; color: white; border: none; min-width: 200px; }
    div.stButton > button:first-child:hover { background-color: #059669; color: white; }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 Etheris Space - Premium Subtitle Translator")
st.caption("Parallel-threaded SRT processing built for Gemini 3.1 & 3.5 series engines.")

# 2. Secure API Key Initialization 
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ Access Key Missing. Please set up GEMINI_API_KEY inside your platform deployment settings to proceed.")
    st.stop()

# Initialize the modern unified Google GenAI client
client = genai.Client(api_key=api_key)

# 3. Dynamic User Configuration Dashboard (With Hover Tooltips Built-In!)
col1, col2, col3 = st.columns(3)

with col1:
    model_choice = st.selectbox(
        "AI Engine Selection", 
        ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"],
        help="• gemini-3.1-flash-lite: Best for hyper-budget scale. Costs 50% less than standard flash.\n\n• gemini-3.5-flash: Delivers high-end localization quality and natural dialogue flows."
    )

with col2:
    chunk_size = st.slider(
        "Lines per Request (Chunk Size)", 
        min_value=20, 
        max_value=150, 
        value=75,
        help="How many subtitle blocks are sent to the AI at one time.\n\n• Low (30-50): Super fast, completely safe, but AI might lose scene context.\n\n• High (120-150): Best story context and dialogue flow, but takes longer per chunk.\n\n💡 Sweet Spot: 75 to 85 lines."
    )

with col3:
    parallel_workers = st.slider(
        "Parallel Active Threads (Speed Control)", 
        min_value=1, 
        max_value=10, 
        value=5,
        help="How many chunks fly out to Google's servers at the exact same time.\n\n• 1 Thread: Safe but slow (sequential processing).\n\n• 5 Threads: 500% faster processing. Great balance.\n\n• 10 Threads: Maximum speed. Safe to use on your paid Tier 1 account without hitting rate limits!"
    )

# 4. SRT Parsing Helper Engine
def parse_srt(srt_text):
    blocks = re.split(r'\n\s*\n', srt_text.strip())
    return [b for b in blocks if b.strip()]

# 5. Core Translation Processing Node
def translate_chunk(chunk_index, chunk_data, model_name):
    system_prompt = f"""You are an expert film localization translator specializing in translating English subtitles into natural, spoken Burmese (လူပြောစကား).

CRITICAL RULES:
1. STRICTLY preserve all original layout formats, chronological timestamps, index integers, and line spaces. Do not alter them.
2. Translate only the conversational or narrative lines. If character headers or production tags are present, preserve them exactly.
3. Keep the translation tone highly natural and contextually appropriate for fluid video dialogue. Do not be formal or literal.

SRT Chunk to Translate:
{chunk_data}
"""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=system_prompt
        )
        
        # Safely extract token tracking data
        input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
        output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
        
        return {
            "index": chunk_index,
            "text": response.text,
            "success": True,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    except Exception as e:
        return {
            "index": chunk_index,
            "text": chunk_data,
            "success": False,
            "error": str(e),
            "input_tokens": 0,
            "output_tokens": 0
        }

# 6. Primary UI Execution Lifecycle
uploaded_file = st.file_uploader("Upload your target English SRT file", type=["srt"])

if uploaded_file is not None:
    srt_content = uploaded_file.read().decode("utf-8")
    blocks = parse_srt(srt_content)
    
    # Slice the file based on the slider setting
    chunks = [blocks[i:i + chunk_size] for i in range(0, len(blocks), chunk_size)]
    st.info(f"Loaded {len(blocks):,} subtitle elements mapped across {len(chunks)} processing chunks.")
    
    if st.button("🚀 Execute Subtitle Translation", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        translated_chunks = [None] * len(chunks)
        total_input_tokens = 0
        total_output_tokens = 0
        error_tracking_count = 0
        
        start_time = time.time()
        
        # Asynchronous Parallel Multi-Threading Loop
        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            future_to_chunk = {
                executor.submit(translate_chunk, idx, "\n\n".join(chunk), model_choice): idx 
                for idx, chunk in enumerate(chunks)
            }
            
            completed = 0
            for future in as_completed(future_to_chunk):
                idx = future_to_chunk[future]
                result = future.result()
                
                translated_chunks[idx] = result["text"]
                total_input_tokens += result["input_tokens"]
                total_output_tokens += result["output_tokens"]
                
                if not result["success"]:
                    error_tracking_count += 1
                
                completed += 1
                progress_bar.progress(completed / len(chunks))
                status_text.text(f"Processing structural volume: {completed}/{len(chunks)} chunks finalized...")
        
        end_time = time.time()
        status_text.empty()
        
        # Reconstruct final file layout
        final_srt = "\n\n".join(translated_chunks)
        
        if error_tracking_count > 0:
            st.warning(f"⚠️ App finished execution with {error_tracking_count} processing errors. Bypassed modules retained English text fields.")
        else:
            st.success(f"🎉 Job completed successfully in {round(end_time - start_time, 1)} seconds!")
        
        # 7. Real-Time Cost Dashboard Interface
        st.markdown(f"""
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 8px; margin-top: 15px; margin-bottom: 20px; font-family: sans-serif;">
                <h4 style="margin: 0 0 12px 0; color: #1e293b;">📊 Execution Cost Analytics Tracker</h4>
                <div style="display: flex; gap: 40px; font-size: 0.95rem; color: #334155;">
                    <p style="margin: 0;">📥 <b>Processed Input:</b> {total_input_tokens:,} tokens</p>
                    <p style="margin: 0;">📤 <b>Generated Output:</b> {total_output_tokens:,} tokens</p>
                    <p style="margin: 0; color: #10b981;">⚙️ <b>Active Host Engine:</b> <code>{model_choice}</code></p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Local File Download Trigger
        st.download_button(
            label="💾 Download Burmese SRT File",
            data=final_srt,
            file_name=f"Burmese_Localized_{uploaded_file.name}",
            mime="text/plain"
        )
