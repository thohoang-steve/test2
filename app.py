import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup
from collections import Counter
import time
from io import BytesIO
from docx import Document

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="SEO Content Researcher", layout="wide")
st.markdown("""<style>.main {background-color: #f4f6f9;} h1 {color: #2c3e50;} .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}</style>""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'results' not in st.session_state: st.session_state['results'] = None
if 'is_analyzed' not in st.session_state: st.session_state['is_analyzed'] = False

# --- HÀM DRIVER (ĐÃ FIX ĐỂ VƯỢT TƯỜNG LỬA) ---
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # Giả lập màn hình thật để không bị phát hiện là Bot
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    # User Agent mới nhất
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- HÀM LÀM SẠCH (AN TOÀN HƠN) ---
def clean_html(soup):
    # Chỉ xóa những thứ chắc chắn là rác
    for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'noscript', 'iframe', 'svg']):
        tag.decompose()
    return soup

# --- GIAO DIỆN ---
st.title("🔎 SEO Content Researcher (Fix Lỗi)")

if not st.session_state['is_analyzed']:
    with st.container():
        urls_input = st.text_area("👉 Dán danh sách URL (Mỗi dòng 1 link):", height=200)
        if st.button("🚀 BẮT ĐẦU PHÂN TÍCH", type="primary"):
            if not urls_input.strip():
                st.warning("Chưa nhập URL!")
            else:
                url_list = [x.strip() for x in urls_input.split('\n') if x.strip()][:5]
                progress = st.progress(0)
                status = st.empty()
                
                all_data = []
                outline_corpus = []
                display_text_full = ""
                
                try:
                    driver = get_driver()
                    for i, url in enumerate(url_list):
                        status.text(f"⏳ Đang xử lý: {url}...")
                        try:
                            driver.get(url)
                            time.sleep(5) # Tăng thời gian chờ lên 5s cho An Cuong
                            
                            # Kiểm tra xem có bị chặn 403 không
                            if "403" in driver.title or "Forbidden" in driver.page_source:
                                st.error(f"❌ Link {url} bị chặn (403 Forbidden).")
                                continue

                            soup = BeautifulSoup(driver.page_source, 'html.parser')
                            
                            # Lấy Meta trước khi Clean
                            title = soup.title.get_text(strip=True) if soup.title else "No Title"
                            meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
                            meta_desc = meta.get('content', '').strip() if meta else "No Description"

                            # Clean và lấy Heading
                            soup = clean_html(soup)
                            headings = soup.find_all(['h1', 'h2', 'h3'])
                            
                            # Nếu không tìm thấy H1-H3, thử tìm thẻ div title (cho web đặc thù)
                            if not headings:
                                st.warning(f"⚠️ Link {url}: Không tìm thấy thẻ H1-H3 chuẩn. Web cấu trúc lạ.")
                            
                            heading_str = []
                            display_text_full += f"\nURL: {url}\nTITLE: {title}\nMETA: {meta_desc}\nSTRUCTURE:\n"
                            
                            for tag in headings:
                                txt = tag.get_text(strip=True)
                                if txt:
                                    tag_name = tag.name.upper()
                                    heading_str.append(f"[{tag_name}] {txt}")
                                    display_text_full += f"- [{tag_name}] {txt}\n"
                                    if tag.name == 'h2': outline_corpus.append(txt)

                            all_data.append({'URL': url, 'Title': title, 'Meta Desc': meta_desc, 'Headings': "\n".join(heading_str)})
                        
                        except Exception as e:
                            st.error(f"Lỗi đọc {url}: {e}")
                        
                        progress.progress((i + 1) / len(url_list))
                    
                    # Logic Gợi ý Outline
                    recommend_list = []
                    recommend_text = ""
                    if outline_corpus:
                        normalized = [h.lower().replace('là gì','').strip() for h in outline_corpus]
                        common = Counter(normalized).most_common(15)
                        recommend_text = "GỢI Ý OUTLINE:\n"
                        for topic, count in common:
                            orig = next((h for h in outline_corpus if h.lower().replace('là gì','').strip() == topic), topic.title())
                            note = f"(x{count})" if count > 1 else ""
                            recommend_text += f"- {orig} {note}\n"
                            recommend_list.append(orig)
                    
                    if not all_data:
                        st.error("❌ Không thu thập được dữ liệu nào! Hãy kiểm tra lại đường link.")
                    else:
                        st.session_state['results'] = {'all_data': all_data, 'display_text': display_text_full, 'rec_text': recommend_text, 'rec_list': recommend_list}
                        st.session_state['is_analyzed'] = True
                        st.rerun()

                except Exception as e:
                    st.error(f"Lỗi Driver: {e}")
else:
    # --- KẾT QUẢ ---
    res = st.session_state['results']
    if st.button("⬅️ QUAY LẠI"):
        st.session_state['results'] = None
        st.session_state['is_analyzed'] = False
        st.rerun()

    c1, c2 = st.columns(2)
    with c1: 
        st.subheader("💡 Outline Đề Xuất")
        st.text_area("Copy:", value=res['rec_text'], height=400)
    with c2:
        st.subheader("📝 Dữ liệu chi tiết")
        st.text_area("Raw Data:", value=res['display_text'], height=400)

    # Xuất file
    st.divider()
    b1, b2 = st.columns(2)
    
    # Word
    doc = Document()
    doc.add_heading('SEO REPORT', 0)
    doc.add_heading('OUTLINE RECOMMEND', 1)
    for i in res['rec_list']: doc.add_paragraph(f"- {i}", style='List Bullet')
    doc.add_heading('RAW DATA', 1)
    for d in res['all_data']:
        doc.add_heading(d['URL'], 2)
        doc.add_paragraph(f"Title: {d['Title']}")
        doc.add_paragraph(f"Desc: {d['Meta Desc']}")
        doc.add_paragraph(d['Headings'])
    
    buf_doc = BytesIO()
    doc.save(buf_doc)
    buf_doc.seek(0)
    with b1: st.download_button("📄 Tải Word (.docx)", buf_doc, "SEO_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

    # Excel
    buf_xls = BytesIO()
    with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as writer:
        df1 = pd.DataFrame(res['all_data'])
        df1.insert(0, 'No.', range(1, 1 + len(df1)))
        df1.to_excel(writer, sheet_name='Outline Research', index=False)
        pd.DataFrame(res['rec_list'], columns=['Recommended H2']).to_excel(writer, sheet_name='Outline Recommend', index=False)
    buf_xls.seek(0)
    with b2: st.download_button("📊 Tải Excel (2 Sheets)", buf_xls, "SEO_Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
