import streamlit as st
st.set_page_config(layout="wide", page_title="Suchassistent Trumpf")

import os
import time
import re
import locale
import numpy as np
from PIL import Image
from init import initialize_database
from parsePDFs import add_pdf, delete_pdf
from cross_encoder import retrieve_cross_encoder
import query_expansion
import log
import bm25_retrieval

# ------------------ Initialisierung ------------------
conn = initialize_database()
query_expansion.update_synonym_list()
bm25, doc_ids = bm25_retrieval.initialize_bm25(conn)
keycaps = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']

# Session-State für Löschvorgänge
if "delete_occurred" not in st.session_state:
    st.session_state.delete_occurred = False
if "deleted_message" not in st.session_state:
    st.session_state.deleted_message = ""

# Helper function to force a reload of the updated list (without full page reload)
def refresh_pdf_list():
    """Liest die aktuelle Liste aus der Datenbank und rendert den PDF-Löschbereich neu.
       Dabei wird für jede Dateiname-Vorkommnis ein eindeutiger Schlüssel erzeugt.
    """
    container = st.container()
    pdf_names = get_db_pdf_names(conn)
    if pdf_names:
        st.write("Verfügbare PDFs zum Löschen:")
        # Verwende ein Wörterbuch, um die Anzahl der Vorkommnisse jedes Dateinamens zu zählen.
        counts = {}
        for pdf in pdf_names:
            if pdf in counts:
                counts[pdf] += 1
            else:
                counts[pdf] = 0
            current_index = counts[pdf]
            cols = container.columns([0.8, 0.2])
            with cols[0]:
                st.markdown(
                    f'<a class="pdf-link" href="http://localhost:9000/data/{pdf}" target="_blank">{pdf}</a>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.button("Löschen", key=f"del_{pdf}_{current_index}", on_click=delete_single_pdf, args=(pdf,))
    else:
        st.info("Keine PDFs zum Löschen verfügbar.")

def reload_pdf_list():
    """Clears the deletion area and re-renders it."""
    st.experimental_rerun()

def process():
    """Verarbeitet das Feedback aus den Suchergebnissen."""
    thumbs_up_vector = []
    thumbs_down_vector = []
    for x in range(st.session_state.topk):
        val = st.session_state.get("crossenc" + str(x))
        if val is None:
            thumbs_up_vector.append(None)
            thumbs_down_vector.append(None)
        elif val == 1:
            thumbs_up_vector.append(1)
            thumbs_down_vector.append(0)
        elif val == 0:
            thumbs_up_vector.append(0)
            thumbs_down_vector.append(1)
    log.log_feedback(
        conn=conn,
        id=st.session_state.id,
        feedback_text=st.session_state.comment,
        pos_ce=thumbs_up_vector,
        neg_ce=thumbs_down_vector,
    )
    st.session_state.thumbs_up = thumbs_up_vector
    st.session_state.thumbs_down = thumbs_down_vector

def get_db_pdf_names(conn):
    """Liefert die in der Datenbank gespeicherten PDF-Dateinamen, alphabetisch sortiert."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM map ORDER BY name ASC;")
    result = cursor.fetchall()
    return [row[0] for row in result]

def delete_all_pdfs():
    """Löscht alle in der Datenbank verzeichneten PDFs und deren Dateien."""
    pdfs = get_db_pdf_names(conn)
    for pdf in pdfs:
        file_path = os.path.join("./data", pdf)
        delete_pdf(conn, file_path)

def delete_single_pdf(pdf):
    """Callback für den 'Löschen'-Button eines einzelnen PDFs."""
    file_path = os.path.join("./data", pdf)
    delete_pdf(conn, file_path)
    st.session_state.deleted_message = f"PDF '{pdf}' wurde erfolgreich gelöscht!"
    st.session_state.delete_occurred = True

# ------------------ UI-Funktionen ------------------

def render_search_tab():
    col1, col2 = st.columns([8, 2])
    with col1:
        st.header("Suchassistent Trumpf 🔍")
    with col2:
        st.image(logo, width=300)
    st.write("")
    query_input = st.text_area("Suchanfrage", key="query", placeholder="Geben Sie eine Suchanfrage ein")
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        search_btn = st.button("Suche", type="primary")
    if search_btn:
        if len(doc_ids) == 0:
            st.warning("Keine Dokumente vorhanden. Bitte fügen Sie zuerst PDFs hinzu!")
        else:
            query = re.sub(r"[()?\[\]{}<>]", "", st.session_state["query"])
            query = query_expansion.expand_query(query)
            st.divider()
            st.subheader("Ergebnisse")
            st.markdown(
                """
                <style>
                div.stSpinner > div {
                    text-align: center;
                    align-items: center;
                    justify-content: center;
                }
                </style>
                """, unsafe_allow_html=True
            )
            with st.spinner("Wird verarbeitet..."):
                scores = bm25_retrieval.retrieve_bm25(bm25, query)
                res = bm25_retrieval.get_retrieved_doc_ids(doc_ids, scores, 10)
                if len(res) == 0:
                    st.info("Keine Treffer gefunden. Bitte versuchen Sie eine andere Suchanfrage!")
                else:
                    temp, runtime = retrieve_cross_encoder(conn, res, query, 10, 10)
                    rank = temp[0]
                    names = temp[1]
                    doc_dict = dict(names)
                    merged_list = [
                        (doc_id, doc_dict[doc_id], page)
                        for doc_id, page in rank if doc_id in doc_dict
                    ]
                    log_id = log.log_data(conn, query, res, [[i, k] for i, k in rank], runtime)
                    st.session_state.id = log_id
                    st.session_state.topk = len(merged_list)
                    with st.form("feedback_form:"):
                        for idx in range(len(merged_list)):
                            sub_col1, sub_col2 = st.columns([8, 2])
                            doc_id = merged_list[idx][0]
                            name = merged_list[idx][1]
                            page = merged_list[idx][2]
                            pdf_url = f"http://localhost:9000/data/{name}#page={page}"
                            with sub_col1:
                                st.page_link(
                                    pdf_url,
                                    label=name.split("/")[-1] + f" :: Seite {page}",
                                    icon=keycaps[idx],
                                )
                            with sub_col2:
                                st.feedback("thumbs", key="crossenc" + str(idx))
                        st.text_area("Anmerkungen", key="comment")
                        submitted = st.form_submit_button("Abschicken", on_click=process)

def render_pdf_upload_tab():
    uploaded_files = st.file_uploader(
        "Ziehen Sie Ihre PDF-Dateien hierher oder klicken Sie auf „Durchsuchen“, um sie auszuwählen (Standard: max. 200 MB).",
        type=["pdf"],
        key="pdf_upload",
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.write("Ausgewählte Dateien (maximal 5 werden direkt angezeigt):")
        for pdf in uploaded_files[:5]:
            st.write(f"- {pdf.name}")
        if len(uploaded_files) > 5:
            with st.expander("Alle ausgewählten Dateien anzeigen"):
                for pdf in uploaded_files:
                    st.write(f"- {pdf.name}")
        if st.button("Ausgewählte PDFs hinzufügen"):
            with st.spinner("Lade Dateien hoch..."):
                temp_dir = "temp_upload"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                for pdf in uploaded_files:
                    temp_file_path = os.path.join(temp_dir, pdf.name)
                    with open(temp_file_path, "wb") as f:
                        f.write(pdf.getbuffer())
                    add_pdf(conn, temp_file_path)
                st.success(f"{len(uploaded_files)} PDF(s) wurden erfolgreich hinzugefügt!")
                time.sleep(2)
                st.experimental_rerun()

def render_pdf_delete_tab():
    # Zeige Erfolgsmeldung (falls vorhanden) oberhalb der Liste
    if st.session_state.delete_occurred:
        st.success(st.session_state.deleted_message)
        time.sleep(2)
        st.session_state.delete_occurred = False
        st.session_state.deleted_message = ""
        refresh_pdf_list()
    if st.button("Alle PDFs löschen", key="delete_all"):
        pdfs = get_db_pdf_names(conn)
        if pdfs:
            delete_all_pdfs()
            st.success("Alle PDFs wurden erfolgreich gelöscht!")
            time.sleep(2)
            refresh_pdf_list()
        else:
            st.info("Keine PDFs vorhanden, die gelöscht werden könnten.")
    st.write("")
    st.write("Verfügbare PDFs zum Löschen:")
    refresh_pdf_list()

# ------------------ Hauptprogramm ------------------
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
logo = Image.open("PAL-logo.png")

st.markdown(
    """
    <style>
    .pdf-link {
        color: #1a0dab;
        text-decoration: underline;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True
)

# Erstelle die zwei Haupt-Tabs: "Suche" und "PDF-Verwaltung"
suche_tab, pdf_mgmt_tab = st.tabs(["Suche", "PDF-Verwaltung"])

with suche_tab:
    render_search_tab()

with pdf_mgmt_tab:
    st.header("PDF-Verwaltung")
    upload_tab, delete_tab = st.tabs(["PDFs hochladen", "PDFs löschen"])
    with upload_tab:
        render_pdf_upload_tab()
    with delete_tab:
        render_pdf_delete_tab()
