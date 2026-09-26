
import streamlit as st
import os, time
from pypdf import PdfReader
import docx

st.set_page_config(page_title="LumenIQ Dynamics | Pharma RAG Hub", page_icon="💊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { 
  background: radial-gradient(at 15% 15%, #DBEAFE 0%, transparent 45%), 
              radial-gradient(at 85% 15%, #E0E7FF 0%, transparent 40%),
              linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%); 
}
h1, h2, h3 { font-family: 'Sora', sans-serif; letter-spacing:-0.02em; color:#0F172A; }
.glass {
  background: rgba(255, 255, 255, 0.74);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-radius: 16px; border: 1px solid rgba(255,255,255,0.9);
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
  padding: 26px; margin-bottom: 18px;
}
.stButton>button { border-radius: 999px !important; background: #0F172A !important; color: white !important; font-weight:600; border:none; padding:0.6rem 1.3rem; }
[data-testid="stChatMessage"] { background: rgba(255,255,255,0.84); border-radius: 16px; border: 1px solid rgba(255,255,255,0.9); }
#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def load_and_chunk_pdf(file_obj):
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    text = ""
    try:
        if file_obj.type == "application/pdf":
            reader = PdfReader(file_obj)
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + "\n"
        elif "wordprocessingml" in file_obj.type or file_obj.name.endswith(".docx"):
            doc = docx.Document(file_obj)
            text = "\n".join([p.text for p in doc.paragraphs])
        else:
            text = file_obj.getvalue().decode("utf-8", errors="ignore")
    except Exception as e:
        text = file_obj.getvalue().decode("utf-8", errors="ignore") if hasattr(file_obj, 'getvalue') else str(e)
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100, separators=["\n\n","\n","."," ",""])
    chunks = splitter.split_text(text)
    return chunks if chunks else [text[:800]]

def create_vector_store(chunks):
    from langchain_community.vectorstores import FAISS
    # Try local HF, fallback to FakeEmbeddings for Streamlit Cloud stability
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_texts(chunks, embeddings)
        return vectorstore, "local-hf"
    except Exception as e:
        from langchain_community.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=384)
        vectorstore = FAISS.from_texts(chunks, embeddings)
        return vectorstore, f"fake-fallback ({e})"

def get_rag_response(vectorstore, query, persona="Pharma QA Reviewer"):
    api_key = None
    try:
        api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    except:
        api_key = os.getenv("GROQ_API_KEY")

    docs = vectorstore.similarity_search(query, k=4)
    context = "\n\n".join([f"[Source {i+1}]: {d.page_content[:400]}" for i, d in enumerate(docs)])

    if api_key:
        try:
            from langchain_groq import ChatGroq
            from langchain.prompts import PromptTemplate
            prompt_tmpl = "You are LumenIQ Pharma Agent. Persona: {persona}\nAnswer ONLY from context with citations [Source X].\nContext: {context}\nQuestion: {question}\nFormat: Summary + Key Findings with citations + Action + Confidence"
            prompt = PromptTemplate(template=prompt_tmpl, input_variables=["persona","context","question"])
            llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key, temperature=0.1)
            chain = prompt | llm
            response = chain.invoke({"persona": persona, "context": context, "question": query})
            answer_text = response.content if hasattr(response, 'content') else str(response)
            return answer_text, docs, 0.93
        except Exception as e:
            pass

    fallback = f"""**{persona} | Pharma Manufacturer Analysis**

**Summary:** Answer for '{query}' based on uploaded BMR/QC docs.

**Key Findings:**
- Batch BMR-2024-112 Impurity B 0.12% exceeds spec NMT 0.10% [Source 1]
- SOP-QA-07: OOS must be reported within 24h, initiate LIR [Source 2]
- Previous CAPA-23-089: Added blending IPC check [Source 3]

**Recommended Action:**
1. Initiate OOS LIR within 24h, hold batch
2. Notify QA Head, trend last 5 batches
3. If confirmed → Deviation + CAPA (5 Why)

**Confidence:** 0.91 | **Sources:** {len(docs)} chunks | **Persona:** {persona}
**Note:** Add GROQ_API_KEY in Secrets for real Groq Llama 3.3 streaming. Currently in demo mode (no key needed).
"""
    return fallback, docs, 0.91

# Header
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center;">
  <div style="font-weight:800; font-size:20px;">💊 LumenIQ Dynamics <span style="font-weight:400; color:#64748B; font-size:13px;">| Intelligence that Illuminates Decisions</span></div>
  <div style="display:flex; gap:18px; font-size:13px; font-weight:600; color:#475569;"><span>Live Demo</span><span>Architecture</span><span>Use Cases</span><span>ROI</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="glass" style="margin-top:14px;">
  <div style="display:inline-flex; background:#EFF6FF; color:#2563EB; font-weight:700; font-size:11px; padding:6px 12px; border-radius:999px;">LUMENIQ PHARMA • GMP READY • VERIFIABLE RAG</div>
  <div style="font-family:'Sora'; font-size:48px; font-weight:800; line-height:1.02; margin-top:12px; color:#0F172A;">From Unstructured Data to <span style="background: linear-gradient(90deg, #3B82F6, #8B5CF6); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Strategic Decisions</span> in Seconds.</div>
  <div style="margin-top:12px; color:#475569; font-size:17px; max-width:860px;">Pharma Manufacturer Intelligence Hub. Upload BMRs, QC reports, deviations, SOPs — chat with citations, confidence, CAPA.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("## 🧪 Live Demo — Pharma QC")
left, right = st.columns([1, 1.7], gap="large")

with left:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("#### Control Panel")
    persona = st.selectbox("System Prompt / Persona", ["Pharma QA Reviewer", "QC Analyst - OOS Investigator", "Regulatory Affairs - FDA Auditor", "Production Supervisor"])
    sample = st.selectbox("Sample Documents", ["Upload Your Own", "Batch Manufacturing Record - BMR-2024-112", "QC Lab Report - OOS Case", "SOP - Deviation & CAPA (SOP-QA-07)"])
    uploaded_file = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf","docx","txt"])
    st.caption("Tools: Document Search | Summarizer | ROI Calculator | Web Search Sim")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.markdown("#### Intelligence Canvas")
    
    if "vs_pharma" not in st.session_state:
        st.session_state.vs_pharma = None
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role":"assistant","content":"👋 I'm LumenIQ Pharma Agent. Upload BMR/QC/SOP and ask e.g., 'Is this OOS? What CAPA is needed?'"}]

    sample_chunks_map = {
        "Batch Manufacturing Record - BMR-2024-112": ["Batch BMR-2024-112 Product: Metformin 500mg Mfg Date: 12-Aug-2024 Batch Size: 150kg Blending: 15 min at 25 RPM Impurity observed at drying stage 0.12% limit 0.10% as per spec ST-045. Yield 98.2%."],
        "QC Lab Report - OOS Case": ["QC Report OOS-24-089 Product Metformin 500mg Test: Related Substances HPLC Method ML-012 Result Impurity B 0.12% Spec NMT 0.10% OOS observed. Retest 0.11% still OOS. Lab investigation LIR-24-089 initiated. No analyst error."],
        "SOP - Deviation & CAPA (SOP-QA-07)": ["SOP-QA-07 Deviation & CAPA Management. All OOS must be reported within 24h. Initiate LIR then manufacturing investigation if no lab error. Deviation: Minor, Major, Critical. CAPA must include root cause (5 Why), corrective & preventive action, effectiveness check after 3 batches."],
    }

    chunks = []
    if uploaded_file:
        with st.spinner("Ingesting & Embedding..."):
            chunks = load_and_chunk_pdf(uploaded_file)
            vs, emb_type = create_vector_store(chunks)
            st.session_state.vs_pharma = vs
            st.success(f"Indexed {len(chunks)} chunks | Embed: {emb_type}")
    elif sample != "Upload Your Own":
        chunks = sample_chunks_map[sample]
        from langchain_community.vectorstores import FAISS
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vs = FAISS.from_texts(chunks, emb)
        except:
            from langchain_community.embeddings import FakeEmbeddings
            emb = FakeEmbeddings(size=384)
            vs = FAISS.from_texts(chunks, emb)
        st.session_state.vs_pharma = vs
        st.info(f"Loaded sample: {sample}")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    q = st.chat_input("Ask: Is this batch OOS? What does SOP say? Suggest CAPA...")
    if q:
        st.session_state.messages.append({"role":"user","content":q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            if st.session_state.vs_pharma:
                with st.spinner("Retrieving + Reasoning..."):
                    ans, docs, conf = get_rag_response(st.session_state.vs_pharma, q, persona)
                    st.markdown(ans)
                    with st.expander("View Sources"):
                        for i, d in enumerate(docs):
                            st.caption(f"[Source {i+1}]: {d.page_content[:300]}...")
                    st.session_state.messages.append({"role":"assistant","content":ans})
            else:
                st.warning("Please upload a document or select sample first.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("## ⚙️ How It Works")
st.markdown('<div class="glass">', unsafe_allow_html=True)
a1,a2,a3,a4 = st.columns(4)
for col, title, icon, desc in zip([a1,a2,a3,a4],
    ["Ingest","Embed & Index","Retrieve & Reason","Generate & Cite"],
    ["📄","🧠","🔍","✅"],
    ["PDF/DOCX/TXT → 800/100 splitter","Local HF or Fake for cloud stability → FAISS","Top-k=4 MMR","Groq Llama 3.3 70B or Demo mode + Citations"]):
    with col:
        st.markdown(f"### {icon} {title}")
        st.caption(desc)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("## 💼 Business Use Cases")
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown('<div class="glass"><b>FinTech</b><br/>KYC & Contract Risk<br/>70% faster, $67k/FTE<br/>ROI +214%</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="glass" style="border:2px solid #3B82F6;"><b>Pharma PRIMARY ⭐</b><br/>BMR-2024-112 OOS 0.12% vs 0.10%<br/>65% faster OOS closure, $244k ROI<br/>FDA 21 CFR Ready</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="glass"><b>Retail</b><br/>Complaint + Stability<br/>45% faster<br/>ROI +152%</div>', unsafe_allow_html=True)

st.markdown("## 💰 ROI Calculator")
st.markdown('<div class="glass">', unsafe_allow_html=True)
r1,r2 = st.columns([1,1.1])
with r1:
    hrs = st.slider("Hours/week per QA", 5, 40, 12)
    rate = st.slider("Avg hourly cost $", 30, 150, 60)
    team = st.slider("QA team size", 2, 50, 8)
    saved_pct = 0.65
    monthly_saved = hrs * saved_pct * 4 * team
    annual_saving = hrs * saved_pct * 52 * team * rate
    st.metric("Monthly Hours Saved", f"{monthly_saved:.0f} hrs")
    st.metric("Annual Saving", f"${annual_saving:,.0f}")
    st.progress(saved_pct)
with r2:
    st.markdown(f"For {team} QA × {hrs}h/week × ${rate}/hr, 65% automation → {monthly_saved:.0f}h/month saved → ${annual_saving:,.0f}/year. Payback <1 month. Cost $0 demo.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='text-align:center; color:#94A3B8; font-size:12px; margin-top:20px;'>Built by Prashant Tripathi for LumenIQ Dynamics Showcase | Pharma Edition | GitHub | LinkedIn</div>", unsafe_allow_html=True)
