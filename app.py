import streamlit as st
import json
import os
from cortex import CortexClient
from sentence_transformers import SentenceTransformer
from groq import Groq  

# CONFIG & STYLING 
st.set_page_config(page_title="OncoPhrase", page_icon="🧬", layout="wide")


GROQ_API_KEY = "Key_here" 
client_groq = Groq(api_key=GROQ_API_KEY)

# CACHED RESOURCES
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_data
def load_records():
    file_path = "merged_cancer_records_all_sources.json"
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        return [] 
    with open(file_path, "r") as f:
        return json.load(f) 

# Initialize
model = load_model()
records_list = load_records()

# UI LAYOUT
col_logo , col_text = st.columns([1,5])
with col_logo:
    st.image("OncoPhrase_Logo.png")
    with col_text:
        st.title("OncoPhrase")
        st.markdown("""
            **OncoPhrase leverages vector embeddings and biomedical knowledge graphs to enable semantic search across Hetionet, PubMed, ClinicalTrials.** \\
            Search the Knowledge Graph:
            Find genes, compounds, and diseases associated with cancer using Vector Search powered by **Actian VectorAI**.
        """)
        

st.divider()

with st.form("search_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("Enter Query:", placeholder="e.g. Lung Cancer Genes or TP53")
    with col2:
        st.write("##") 
        submit_button = st.form_submit_button("Search")

# SEARCH LOGIC 
if submit_button and query:
    if not records_list:
        st.warning("Data records are missing.")
    else:
        with st.spinner("Retrieving biological relationships..."):
            try:
                # A. Embed the  query
                q_emb = model.encode(query).tolist()
                
                # B. Call the Actian Docker Container
                with CortexClient("localhost:8000") as client:
                    results = client.search("hetionet_final", query=q_emb, top_k=10)
                
                # C. Display Results
                if not results:
                    st.info("No matching relationships found.")
                else:
                    
                    context_for_ai = ""
                    results_html = []
                    
                    
                    for res in results:
                        try:
                            idx = int(res.id) 
                            if idx < len(records_list):
                                record = records_list[idx]
                                
                                # Add this text to AI context pool
                                context_for_ai += f"\n- {record.get('search_text')}"
                            
                                results_html.append({
                                    "name":record.get('name','Unknown'),
                                    "score":res.score,
                                    "type":record.get('entity_type',"N/A"),
                                    'context':record.get('search_text','N/A')
                                })
                        except (ValueError, TypeError):
                            st.error(f"Invalid ID format: {res.id}")

    
                    st.divider()
                    st.subheader("Analysis")
                    
                    
                    if context_for_ai:
                        with st.spinner("Summarizing biological relationships..."):
                            chat_completion = client_groq.chat.completions.create(
                                messages=[
                                    {
                                        "role": "system", 
                                        "content": "You are a senior bioinformatician. Summarize the biological relationships found in the provided Hetionet data. Be specific about genes and diseases."
                                    },
                                    {
                                        "role": "user", 
                                        "content": f"Context: {context_for_ai}\n\nQuestion: {query}"
                                    }
                                ],
                                model="llama-3.3-70b-versatile",
                            )
                            st.success(chat_completion.choices[0].message.content)
                    st.divider()
                    st.subheader("Hits")
                    with st.expander("Hits Found)"):
                        st.caption(f"Retrieved {len(results_html)} nodes from the Graph")
                        for item in results_html:
                            score_color = "green" if item['score'] > 0.5 else "orange"
                            st.write(f"**{item['name']}** — (Rel: :{score_color}[{item['score']:.3f}])")
                            st.write(f"Type: {item['type']}")
                            st.info(item['context'])

            except Exception as e:
                st.error(f"Connection Error: {e}")

# FOOTER
st.divider()

st.markdown("""
    <style>
    .footer-row {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 30px;
        padding-top: 10px;
    }
    .footer-row img {
        height: 35px; /* Adjust this to make them all smaller/larger */
        width: auto;
        opacity: 0.8;
    }
    .footer-text {
        font-size: 0.85rem;
        color: #888;
        margin-right: 20px;
    }
    </style>
    
    <div class="footer-row">
        <span class="footer-text">Hackalytics 2026 | Powered By:</span>
        <img src="https://www.actian.com/wp-content/uploads/2024/12/Actian-Logo-CMYK_Vertical.png" title="Actian VectorAI">
        <img src="https://miro.medium.com/v2/resize:fit:1400/1*lumgK1pd1FSCkEq3goHLoQ.png" title="Hugging Face">
        <img src="https://cdn.worldvectorlogo.com/logos/docker-4.svg" title="Docker">
        <img src="https://miro.medium.com/v2/resize:fit:1200/1*b9wiAr_HG6ct7uYtCnf0xA.png" title="Groq">
    </div>
    """, unsafe_allow_html=True)