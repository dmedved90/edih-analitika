# EDIH ADRIA analitika v.5 31.10.2025. 19:00
# Updated for Streamlit 1.50.0 and latest libraries

import warnings
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from openai import OpenAI
import numpy as np
import pydeck as pdk
from pathlib import Path
import fitz  # PyMuPDF
import base64, io, json, os, time, random, glob
from io import BytesIO
import plotly.io as pio

# 🌈 GLOBALNA PLOTLY TEMA (EDIH vizualni identitet)
pio.templates["edih_theme"] = pio.templates["plotly_white"]

# Podešavanje boja i fontova
pio.templates["edih_theme"].layout.update(
    font=dict(family="Arial, sans-serif", size=14, color="#333333"),
    title=dict(font=dict(size=20, color="#222222"), x=0.02, xanchor="left"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=40, t=80, b=60),
    coloraxis_colorbar=dict(title_font=dict(size=14)),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5,
        font=dict(size=13)
    )
)

# Zadana kvalitativna (kategorijska) paleta — harmonična i visoko kontrastna
default_colors = px.colors.qualitative.Vivid  # alternativno: Plotly, Bold, Prism
EDIH_CONTINUOUS_SCALE = "Tealgrn"  # ili "Agsunset", "Tealgrn", "Blues", "Viridis"

# Aktiviraj EDIH temu globalno
pio.templates.default = "edih_theme"

# --- Automatska provjera preglednika (sažeta sidebar verzija) ---
with st.sidebar:
    st.markdown("### 🌐 Provjera preglednika")

    components.html("""
        <div id="browser-info" style="font-family:sans-serif; font-size:14px;"></div>
        <script>
          const ua = navigator.userAgent.toLowerCase();
          let msg = "";
          if (ua.includes("edg/")) {
            msg = "✅ Koristite <b>Microsoft Edge</b> — potpuno podržan preglednik.";
          } else if (ua.includes("chrome/")) {
            msg = "✅ Koristite <b>Google Chrome</b> — optimalne performanse.";
          } else if (ua.includes("firefox/")) {
            msg = "⚠️ Koristite <b>Firefox</b> — preporučujemo Chrome ili Edge radi boljih performansi.";
          } else if (ua.includes("safari/")) {
            msg = "🚫 Koristite <b>Safari</b> — nije u potpunosti podržan. Preporučujemo Chrome ili Edge.";
          } else {
            msg = "ℹ️ Nepoznati preglednik — preporučujemo Chrome ili Edge.";
          }
          document.getElementById("browser-info").innerHTML = msg;
        </script>
    """, height=50)

# Suppress openpyxl data validation warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Folder where CSV or XML data will be saved

app_folder = str(Path.home() / "EDIH")
data_folder = os.path.join(app_folder, "Data")
dma_folder = os.path.join(app_folder, "DMA")
slike_folder = os.path.join(app_folder, "Slike")

CATEGORIES = {"SME": os.path.join(dma_folder, "SME"),
              "PSO": os.path.join(dma_folder, "PSO")}

# os.makedirs(data_folder, exist_ok=True)

st.set_page_config(
    page_title="EDIH Services Analysis Dashboard",
    page_icon=slike_folder + "/Edih-Adria-svijetli.ico",
    layout="wide",
    initial_sidebar_state="expanded")


# Deepseek or OpenAI  API KEY
# client = st.secrets["deepseek"]["api_key"]
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# Load the Excel file into a DataFrame
@st.cache_data(show_spinner=False)
def load_data(file_path, sheet_name):
    """Generic loader for standard Excel files (no special date parsing)."""
    data = pd.read_excel(file_path, sheet_name)

    # Clean column headers to avoid hidden spaces or encodings
    data.columns = data.columns.str.strip().str.replace('\u00a0', ' ', regex=False)

    # If 'Dates' exists (rarely), just copy it through for reference
    if 'Dates' in data.columns and 'Start Date' not in data.columns:
        st.info(f"'{sheet_name}' contains a Dates column but is not parsed (using as text).")

    return data.copy()

# Custom loader just for Services
@st.cache_data(show_spinner=False)
def load_uploaded_services(file_path, sheet_name):

    data = pd.read_excel(file_path, sheet_name)

    # 🧹 Clean headers (remove hidden spaces or encodings)
    data.columns = data.columns.str.strip().str.replace('\u00a0', ' ', regex=False)

    # --- Special handling for text-based "Dates" column ---
    if 'Dates' in data.columns:
        # Normalize text and split cleanly
        data['Dates'] = data['Dates'].astype(str).str.strip()
        data['Dates'] = data['Dates'].str.replace(r'\s*/\s*', ' / ', regex=True)

        # Split into Start / End date parts
        date_split = data['Dates'].str.split(' / ', expand=True)
        date_split = date_split.reindex(columns=[0, 1]).fillna('')

        # Convert to datetime safely
        data['Start Date'] = pd.to_datetime(
            date_split[0].str.strip(), errors='coerce', format='%Y-%m-%d'
        )
        data['End Date'] = pd.to_datetime(
            date_split[1].str.strip(), errors='coerce', format='%Y-%m-%d'
        )

        # 🧩 If End Date missing, fill with Start Date
        missing_end_mask = data['End Date'].isna() & data['Start Date'].notna()
        data.loc[missing_end_mask, 'End Date'] = data.loc[missing_end_mask, 'Start Date']

        # Derive years
        data['Start Year'] = data['Start Date'].dt.year
        data['End Year'] = data['End Date'].dt.year

        invalid_starts = data[data['Start Date'].isna()]
        invalid_ends = data[data['End Date'].isna()]

        if not invalid_starts.empty or not invalid_ends.empty:
            st.warning(
                f"⚠️ Some invalid dates in {sheet_name}: "
                f"{len(invalid_starts)} start, {len(invalid_ends)} end"
            )
    else:
        # Fallback in case column missing
        st.warning("📄 'Dates' column not found in Sheet1. Creating empty date fields.")
        data['Start Date'] = pd.NaT
        data['End Date'] = pd.NaT
        data['Start Year'] = np.nan
        data['End Year'] = np.nan

    return data.copy()

# Geocode addresses to get latitude and longitude
def geocode_addresses(data, file_path):
    geolocator = Nominatim(user_agent="edih_geocoder")

    # Check if Latitude and Longitude exist and are populated
    if 'latitude' not in data.columns or 'longitude' not in data.columns:
        data['latitude'] = None
        data['longitude'] = None

    for index, row in data.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            try:
                location = geolocator.geocode(row['Location'], timeout=10) # Address field
                if location:
                    data.at[index, 'latitude'] = location.latitude
                    data.at[index, 'longitude'] = location.longitude
            except GeocoderTimedOut:
                time.sleep(1)  # To avoid overloading the geocoding service

    # Save the updated data back to the file
    data.to_excel(file_path, index=False)
    return data

#Function to summarize text using AI (latest API syntax for openai>=1.0.0 od DeepSeek)
def summarize_text(text, max_tokens=1500):
    try:
        response = client.chat.completions.create(
            model= "gpt-4o-mini",  # Or "deepseek-chat" Or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are an AI assistant that summarizes long reports into key insights."},
                {"role": "user", "content": f"Summarize this report:\n{text}"}
            ],
            stream=False,
            max_tokens=max_tokens,
            temperature=0.3
        )
        # Extract the summary from the response
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error summarizing: {e}"

# PDF OCR and JSON extraction functions

def call_openai_with_retry(payload_func, max_retries=5):
    """Siguran poziv prema OpenAI API-ju s exponential backoff retry logikom."""
    for attempt in range(max_retries):
        try:
            return payload_func()
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait = (2 ** attempt) + random.uniform(0, 1)
                st.warning(f"⚠️ Rate limit reached. Retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            else:
                # Ako je neki drugi error — odmah prekid
                st.error(f"❌ OpenAI error: {e}")
                return None
    st.error("❌ Max retries reached while calling OpenAI API.")
    return None

@st.cache_data(show_spinner=False)
def extract_text_intelligent(pdf_path, use_ocr_model="gpt-4o-mini", dpi=96, delay_between_pages=0.3):
    """
    Ekstraktira tekst iz PDF-a uz automatsku odluku:
      ✅ koristi fitz.get_text() ako PDF ima tekstualni sloj
      ⚙️ koristi GPT-4o OCR samo ako PDF nema čitljiv tekst
      🧠 uključuje rate-limit retry i caching
    """
    doc = fitz.open(pdf_path)
    full_text = ""

    for page_index, page in enumerate(doc):
        text = page.get_text("text")

        if text.strip():
            # ✅ Stranica ima tekstualni sloj
            full_text += text + "\n"
        else:
            # ⚙️ OCR fallback
            st.info(f"OCR: prepoznajem stranicu {page_index + 1}/{len(doc)} ({pdf_path.split('/')[-1]})")
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 96, dpi / 96))
            img_bytes = io.BytesIO(pix.tobytes("png"))
            base64_img = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

            response = call_openai_with_retry(lambda: client.chat.completions.create(
                model=use_ocr_model,
                messages=[
                    {"role": "system",
                     "content": "You are an OCR assistant that extracts text from document images accurately."},
                    {"role": "user",
                     "content": [
                         {"type": "text", "text": "Extract readable text from this page:"},
                         {"type": "image_url",
                          "image_url": {"url": f"data:image/png;base64,{base64_img}", "detail": "high"}}
                     ]}
                ],
                temperature=0.0,
                max_tokens=1000,
            ))

            if response:
                extracted = response.choices[0].message.content.strip()
                full_text += f"\n[OCR Page {page_index + 1}]\n" + extracted + "\n"
            else:
                st.error(f"⚠️ OCR failed for page {page_index + 1} in {pdf_path}")
            
            # Lag između poziva da se izbjegne rate limit
            time.sleep(delay_between_pages)

    return full_text.strip()


def get_summary(organization_name):
    """Vraća sažetak iz JSON-a ili automatski pokreće OCR (s cachingom)."""
    json_file_path = os.path.join(json_folder, f"DMA T0 {organization_name}_extracted.json")
    pdf_file_path = os.path.join(pdf_folder, f"DMA T0 {organization_name}.pdf")

    # Ako JSON već postoji
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return summarize_text(json.dumps(data))

    # Ako nema JSON-a, ali postoji PDF — napravi OCR
    elif os.path.exists(pdf_file_path):
        with st.spinner(f"⚙️ Pokrećem OCR i sumiranje teksta za {organization_name}..."):
            text = extract_text_intelligent(pdf_file_path)
        return summarize_text(text)

    else:
        return f"❌ Nema dostupnog PDF-a ni JSON-a za {organization_name}."


def safe_df(df):
    """Ensure dataframe is fully Arrow- and Streamlit-safe."""
    df = df.copy().reset_index(drop=True)
    df = df.replace({np.nan: None})
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str)
    return df

# --- Helper funkcija za pronalazak najnovije datoteke po prefiksu ---
def get_latest_file(folder, prefix, extension="xlsx"):
    pattern = os.path.join(folder, f"{prefix}*.{extension}")
    files = glob.glob(pattern)
    if not files:
        st.warning(f"Nije pronađena datoteka za prefiks: {prefix}")
        return None
    latest_file = max(files, key=os.path.getmtime)
    # st.info(f"📄 Učitavam najnoviju datoteku: `{os.path.basename(latest_file)}`")
    return latest_file

# --- Cache: učitaj Excel samo jednom ---
@st.cache_data(show_spinner=False)
def load_excel_file(path, sheet_name=None):
    """Učitaj Excel datoteku i očisti nazive kolona."""
    if not path:
        return pd.DataFrame()

    # 1️⃣ Učitaj Excel datoteku
    df = pd.read_excel(path, sheet_name=sheet_name)

    # Ako read_excel vrati dict (više sheetova)
    if isinstance(df, dict):
        first_sheet = list(df.keys())[0]
        # st.warning(f"⚠️ Datoteka {os.path.basename(path)} ima više listova — koristi se '{first_sheet}'")
        df = df[first_sheet]

    # 2️⃣ Očisti nazive kolona
    df.columns = (
        df.columns.astype(str)
        .str.replace('"', '')
        .str.replace("'", "")
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )

    return df

# PDF & JSON folder location
pdf_folder = app_folder + "/DMA/SME"
json_folder = app_folder + "/DMA/SME/JSON"

# --- Automatsko učitavanje najnovijih datoteka iz data_foldera ---

# 1️⃣ EDIH Services (posebna funkcija koja dodaje dodatne kolone)
file_services = get_latest_file(data_folder, "EDIH_uploaded_services_")
if file_services:
    data = load_uploaded_services(file_services, "Sheet1")
    # st.success("✅ EDIH Services učitani s dodatnim kolumnama (Start/End Year, trajanje, datumi, itd.)")
else:
    data = pd.DataFrame()
    st.warning("⚠️ EDIH Services datoteka nije pronađena.")

# 2️⃣ SME i PSO - Reporting
file_SME = get_latest_file(data_folder, "export-sme-")
data_sme = load_excel_file(file_SME, sheet_name="Reporting of EDIH services del")

file_PSO = get_latest_file(data_folder, "export-pso-")
data_pso = load_excel_file(file_PSO, sheet_name="Reporting of EDIH services del")

# 3️⃣ DMA rezultati
file_SME_Ana = get_latest_file(data_folder, "my-smes-dma-results-")
data_smea = load_excel_file(file_SME_Ana, sheet_name="My SMEs DMA Results")

file_PSO_Ana = get_latest_file(data_folder, "my-psos-dma-results-")
data_psoa = load_excel_file(file_PSO_Ana, sheet_name="My PSOs DMA Results")

# 4️⃣ Evidencija zahtjeva
file_zahtjevi = get_latest_file(data_folder, "evidencija-zahtjeva-")
ps_data = load_excel_file(file_zahtjevi, sheet_name="Korisnici - javni sektor")
sme_data = load_excel_file(file_zahtjevi, sheet_name="Skupni podaci Zahtjeva-poduzeća")

# 5️⃣ EDIH EU lista
file_edih_list = get_latest_file(data_folder, "updated_edih_list_with_columns_")
edih_data = load_excel_file(file_edih_list)

# Geocode if needed
# edih_data = geocode_addresses(edih_data, file_edih_list)

# Main Title
# st.title("EDIH Services Analysis Dashboard")

# Layout for analysis and gauges
col1, col2 = st.columns((6, 2), gap='small', vertical_alignment="top", border=False)

# st.sidebar.subheader("Options ")
# st.sidebar.image("https://edihadria.eu/wp-content/uploads/2023/11/Edih-Adria-logo_posV-vector-150ppi.png", width=300)
# Inject CSS to round image borders in the sidebar
st.sidebar.markdown(
    """
    <style>
    [data-testid="stSidebar"] img {
        border-radius: 15px;  /* Adjust the radius as needed */
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.logo(slike_folder + "/SyntAgent-lila.png",size="large", link="https://syntagent.com")
st.sidebar.image(slike_folder + "/Edih Adria znak+logotip.jpg", width=300)
st.sidebar.title("Analysis Options")

# Add toggle for general filter on specific date
apply_reporting_filter = st.sidebar.checkbox("Midterm Date Filter (30.09.2024)", value=False)

if apply_reporting_filter:
    reporting_date = pd.to_datetime("2024-09-30")
    data = data[data['Start Date'] <= reporting_date]

analysis_type = st.sidebar.selectbox(
        "Select Analysis Type:",
        [
            "EDIH ADRIA Service Overview",
            "EU EDIH Comparison",
            "DMA - Summary",
            "Bootcamp - Summary",
            "TBI - Summary",
            "DAP&FCO - Summary",             
            "Education - Summary",
            "State Aid - Summary",
            "ESG - Summary",
        ]
    )

with st.sidebar.expander("📂 Učitane datoteke"):
    for prefix in ["EDIH_uploaded_services_", "export-sme-", "export-pso-", "my-smes-dma-results-", "my-psos-dma-results-", "evidencija-zahtjeva-", "updated_edih_list_with_columns_"]:
        latest = get_latest_file(data_folder, prefix)
        if latest:
            st.markdown(f"**{prefix}** → `{os.path.basename(latest)}`")


with col1:
# Analysis Functions
    if analysis_type == "EDIH ADRIA Service Overview":
    # Karta sa prikazom korisnika   
        st.subheader("EDIH ADRIA Service Overview")        
        with st.expander("Explanation of Results"):
            st.write("During the first reporting period, foundations for the implementation of EDIH Adria services were established, with procedures, manuals and strategies developed and implementation frameworks put in place. Open calls for each EDIH Adria service were published, and communication strategy developed. A total of 83 Digital Maturity Assessment (DMA) evaluations were conducted. Among these, 32 assessments were conducted for small and medium-sized enterprises (SMEs), and 51 for public institutions (PIs). These assessments were vital for understanding the current state of digital maturity across organizations and identifying areas for further development and support. A total of 7 Digital Innovation and Transformation (DIT) Bootcamps whose main goal is to assist users in drafting their digitalization project idea were held, with 6 dedicated to digital transformation and 1 focused on digital innovation. These workshops engaged 42 participants, 37 PIs took part in the digital transformation sessions and 5 SMEs attended the innovation DIT Bootcamp.") 
            st.write("Test before invest (TBI) was focused on providing support to private and public organizations during the exploratory phase of their digitalization initiatives. The implementation of 895 TBI days (64% of the KPI target) has been contracted, with a total of 38 unique users (54% of the KPI target). As of the end of September 2024, one TBI project for new digital products and services and 6 TBI projects for digital transformation have been finalized. The educational activities encompassed in WP3 (Digital skills and training) were directed towards non-ICT employees from SMEs, MCs and PIs, digital industry employees and technology experts/leaders, as well as internally, towards EDIH Adria partners. External users were selected through an open call promoting single events or series of trainings (called “educational package”). As of the end of September 2024, a total of 2,557 days of training per participant were recorded (65% of the KPI target) across three categories of training.")

            st.write("Follow-up activities to TBI, with the goal of increasing the likelihood of implementation of successful TBI cases include support in developing digitalisation action plans for users (DAP), and cover support with how to fund the digital transformation and where to find (or offer) digital solutions to implement in practice (FCO). Two DAPs (Digitalization Action Plan) and two FCOs (Financial Capability and Opportunity) were contracted in this reporting period (and realized in the meantime). To inform and motivate target users for digital transformation, EDIH Adria has actively engaged in a variety of outreach activities. These include the development of strategic partnerships with industry clusters, regional business support organizations, and other EDIHs in Croatia and across Europe. To support efficient communication, an e-tool was created, and social media accounts were launched on LinkedIn and Facebook, fostering engagement with a broader audience.") 
            st.write("The EDIH Adria annual conference and meetup, held on November 30th, 2023, at the Infobip Quantum facility in Vodnjan, served as a platform for collaboration and knowledge exchange. This event gathered 95 participants, featured 12 speakers, and EDIH annual award was given to PRIGODA – Regional Development Agency of Primorsko-Goranska County for their contributions to the project. During this reporting period we actively worked on the development of a catalogue of regional digital solutions, suppliers, experts, and clusters by leveraging the existing RIMAP platform (Regional Innovation Matchmaking Platform) owned by the University of Rijeka. By building on RIMAP's functionalities and data, this integration streamlined data collection, enhanced matchmaking between academia and industry, and supported knowledge transfer to drive digital transformation in the Adriatic region and beyond.")

            st.write("The activities conducted so far indicate a systematic approach to supporting digitalization, particularly among SMEs and PIs. The European dimension of this project is evident in its alignment with EU goals for digital transformation and innovation, contributing to the broader agenda of enhancing the digital economy across member states. The project adds value by promoting sustainable growth and resilience within SMEs and PIs, ultimately leading to increased competitiveness in the European market.")
        
        map_data = data.dropna(subset=['latitude', 'longitude'])
        map_summary = map_data.groupby(['latitude', 'longitude', 'Customer']).agg(
            total_revenue=('Service price, €', 'sum')
        ).reset_index()
           
        map_summary = map_summary.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        
        # NWE Map Visualization using PyDeck
        st.subheader("EDIH Users on Map")
        
        view_state = pdk.ViewState(
            latitude=map_summary["lat"].mean(),
            longitude=map_summary["lon"].mean(),
            zoom=5,
            pitch=50
        )
        
        layer = pdk.Layer(
                    "HexagonLayer",
                    data=map_summary,
                    get_position="[lon, lat]",
                    auto_highlight=True,
                    radius=1000,
                    elevation_scale=10,
                    elevation_range=[0, 3000],
                    pickable=True,
                    extruded=True,
                    get_elevation="total_revenue",
                    
        )
        # tooltip = {"html": "<b>Customer:</b> {Customer}<br><b>Total Revenue (€):</b> {total_revenue}"}
        # tooltip = {"html": "<b>Number of Customers:</b> {num_customers}<br><b>Total Revenue (€):</b> {total_revenue}"}
          

        edih_map = pdk.Deck(
            # map_style="mapbox://styles/mapbox/light-v9",
            map_style=None,
            initial_view_state=view_state,
            # tooltip=tooltip,
            layers=[layer]
        )
        
        st.pydeck_chart(edih_map)

        
        # Delivered Services by Region
        regional_summary = data.groupby('Customer  region').agg(
            total_services=('Content ID', 'count'),
            total_revenue=('Service price, €', 'sum')
        ).reset_index().sort_values(by='total_revenue', ascending=False)
        # st.subheader("Regional Summary")
        
        fig = px.bar(
            regional_summary,
            x='Customer  region',
            y='total_services',
            title='Delivered Services by Region',
            labels={'total_services': 'Number of Services', 'Customer region': 'Region'},
            text='total_services'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(regional_summary, width=True)
            st.table(regional_summary)

        # Delivered Services by Category      
        service_summary = data.groupby('Service category delivered').agg(
            total_services=('Content ID', 'count'),
            total_revenue=('Service price, €', 'sum')
        ).reset_index().sort_values(by='total_revenue', ascending=False)
        # st.subheader("EDIH Adria Service Overview")
        # st.write(service_summary)
        fig = px.bar(
            service_summary,
            x='Service category delivered',
            y='total_services',
            color="total_services",
            color_continuous_scale=EDIH_CONTINUOUS_SCALE,
            title='Delivered Services by Category',
            labels={'total_services': 'Number of Services', 'Service category delivered': 'Category'},
            text='total_services'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(safe_df(service_summary), width=True)
            st.table(service_summary)

       # Technology applied in EDIH ADRIA Services
        # st.subheader("Applied Technologies")
        # Ensure relevant columns are numeric
        numeric_cols = ['Content ID', 'Service price, €', 'Number of attendees']

        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')  # Convert and coerce errors to NaN

        technology_summary = data.groupby('Technology type used').agg(
            total_services=('Content ID', 'count'),
            total_revenue=('Service price, €', 'sum'),
            total_attendees=('Number of attendees', 'sum')
        ).reset_index().sort_values(by='total_revenue', ascending=False)

        # Ako ima puno tehnologija, spoji manje u "Other"
        max_segments = 7  # koliko najvećih zadržati
        if len(technology_summary) > max_segments:
            top = technology_summary.nlargest(max_segments, "total_services")
            others = technology_summary.iloc[max_segments:]
            other_row = pd.DataFrame({
                "Technology type used": ["Other"],
                "total_services": [others["total_services"].sum()],
                "total_revenue": [others["total_revenue"].sum()],
                "total_attendees": [others["total_attendees"].sum()]
            })
            technology_summary = pd.concat([top, other_row], ignore_index=True)

        # Skrati nazive tehnologija za prikaz na grafu
        def shorten_label(label, max_length=25):
            return label if len(label) <= max_length else label[:max_length] + "…"

        technology_summary["Short Label"] = technology_summary["Technology type used"].apply(shorten_label)

        fig = px.pie(
            technology_summary,
            names='Short Label',
            values='total_services',
            hover_name="Technology type used",  # puni naziv u tooltipu
            title='Technologies applied in EDIH ADRIA Services',
            color_discrete_sequence=px.colors.qualitative.Vivid,
            hole=0.4
        )

        fig.update_traces(
            textinfo="label+percent",
            textposition="outside",
            showlegend=False,
            pull=[0.05]*len(technology_summary),  # malo izvuci segmente radi preglednosti
        )

        fig.update_layout(
            uniformtext_minsize=10,
            uniformtext_mode="hide",
            margin=dict(t=80, b=60, l=40, r=40),
            height=600
        )        

        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})

        with st.expander("Tabular data"):    
            # st.dataframe(safe_df(technology_summary), width=True)
            st.table(technology_summary)
        
        # Delivered Services by Customer Staff Size

        customer_size_analysis = data.groupby('Customer staff size').agg(
            total_services=('Content ID', 'count'),
            total_revenue=('Service price, €', 'sum')
        ).reset_index().sort_values(by='total_revenue', ascending=False)
        # st.subheader("Customer Staff Size Summary")
        # st.write(customer_size_analysis)
        fig = px.bar(
            customer_size_analysis,
            x='Customer staff size',
            y='total_services',
            color="total_services",
            color_continuous_scale=EDIH_CONTINUOUS_SCALE,
            title='Delivered Services by Customer Staff Size',
            labels={'total_services': 'Number of Services', 'Customer staff size': 'Staff Size'},
            text='total_services'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(safe_df(customer_size_analysis), width=True)
            st.table(customer_size_analysis)

        # Services Delivered by Year 
        # st.write(list(data.columns))      
        yearly_summary = data.groupby('Start Year').agg(
            total_services=('Content ID', 'count'),
            total_revenue=('Service price, €', 'sum')
        ).reset_index().sort_values(by='Start Year', ascending=True) #total_revenue

        # st.subheader("Yearly Analysis")
        # Pretvori godine u string za pravilno etiketiranje osi
        yearly_summary["Start Year"] = yearly_summary["Start Year"].round().astype(int).astype(str)
        
        # st.write(yearly_summary)
        fig = px.bar(
            yearly_summary,
            x='Start Year',
            y='total_services',
            title='Delivered Services by Year',
            color="total_services",
            color_continuous_scale=EDIH_CONTINUOUS_SCALE,
            labels={'total_services': 'Number of Services', 'Start Year': 'Year'},
            text='total_services'
        )
        # Ručno postavi da je osa kategorička i da se prikazuje po redu godina
        fig.update_xaxes(type="category", categoryorder="array",
                 categoryarray=sorted(yearly_summary["Start Year"].unique()))

        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})
        
        with st.expander("Tabular data"):    
            # st.dataframe(yearly_summary, width=True)
            st.table(yearly_summary)

    elif analysis_type == "EU EDIH Comparison":
        st.subheader("EU EDIH Comparison")
        with st.expander("Explanation of Results"):
            st.write("Despite administrative difficulties in the first year of the project, EDIH ADRIA managed to implement most of the activities and meet most of the targeted goals. According to all indicators, EDIH ADRIA is among the top ten best EU EDIHs in terms of results, published good examples, and participation in numerous international events.")
        # Aggregate number of EDIHs per country
        country_summary = edih_data.groupby("Country").agg(
            num_edihs=("EDIH Name", "count"),
            url=("URL", "first")  # Using first URL as example
        ).reset_index()
        
        # Map Visualization using PyDeck
        # st.subheader("EDIH Locations on Map")
        edih_data = edih_data.dropna(subset=['Latitude', 'Longitude'])
        # Set a minimum radius for points with EDUC = 0 (e.g., 100)
        edih_data["Radius"] = edih_data["EDUC"].apply(lambda x: max(x * 50, 1000))  # Minimum size 100
        
        # Define Map View
        view_state = pdk.ViewState(
            latitude=edih_data["Latitude"].mean(),
            longitude=edih_data["Longitude"].mean(),
            zoom=4,
            pitch=50
        )

        # Define Scatterplot Layer

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=edih_data,
            get_position="[Longitude, Latitude]",
            get_radius="Radius",
            get_color="[200, 30, 0, 160]",
            pickable=True,
            
        )
        # Create Deck Map
        edih_map = pdk.Deck(
            #map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            tooltip={"html": "<b>{EDIH Name}</b><br>Country: {Country}<br>EDUC: {EDUC} <br>DMA: {DMA} <br>TBI: {TBI} <br>FCO: {FCO} <br>NETWORK: {NETWORK}"},
            layers=[layer]
        )
        
        st.pydeck_chart(edih_map)
        
        # Ranking of EDIHs based on DMA, EDUC, TBI, FCO, Network
        ranking_columns = ["DMA", "EDUC", "TBI", "FCO", "NETWORK"]
        ranking_summary = edih_data[["EDIH Name", "Country"] + ranking_columns].sort_values(by=ranking_columns, ascending=False)
        # st.dataframe(ranking_summary, width=True)
        if ranking_columns:
            # ranking_summary = edih_data[["EDIH Name", "Country"] + ranking_columns].sort_values(by=ranking_columns, ascending=False)
            
            # st.subheader("EDIH Ranking by Key Metrics")
            # st.dataframe(ranking_summary, width=True)
            
            # Heatmap Visualization
            ranking_summary = ranking_summary.iloc[::-1]  # Flip the DataFrame vertically
            # Generate Heatmap using go.Heatmap
            fig_heatmap = go.Figure()

            fig_heatmap.add_trace(go.Heatmap(
                z=ranking_summary.set_index("EDIH Name")[ranking_columns].values,  
                x=ranking_columns,  
                y=ranking_summary["EDIH Name"],  
                colorscale="viridis",
                colorbar=dict(title="Score")
            ))

            # Add top x-axis labels using annotations with 45-degree rotation
            annotations = []
            for i, col in enumerate(ranking_columns):
                annotations.append(
                    dict(
                        x=i, 
                        y=len(ranking_summary["EDIH Name"]) + 0.5,  # Position above heatmap
                        text=col, 
                        showarrow=False,
                        font=dict(size=12, color="lightgray")
                        # textangle=45  # Rotate text by 45 degrees
                    )
                )

            # Configure Layout
            fig_heatmap.update_layout(
                title="Heatmap of EDIH Rankings",
                height=2500,
                xaxis=dict(
                    title="Metrics",
                    side="bottom",
                    tickmode="array",
                    tickvals=list(range(len(ranking_columns))),
                    ticktext=ranking_columns
                ),
                yaxis=dict(title="EDIHs"),
                coloraxis=dict(colorscale=EDIH_CONTINUOUS_SCALE),
                annotations=annotations  # Add rotated top x-axis labels
            )          

            st.plotly_chart(fig_heatmap, config={'displayModeBar': True, 'displaylogo': False})
            with st.expander("Tabular data"):    
                # st.dataframe(ranking_summary, width=True)
                st.table(ranking_summary)
        else:
            st.warning("No valid ranking columns found in the dataset.")


    elif analysis_type == "Education - Summary":
        st.subheader("Education - Types of trainings")
        with st.expander("Explanation of Results"):
            st.write("Under the leadership of UNIRI, all project partners participated in the development of the annual strategy for digital skills and training (MS4). For development and implementation of the strategy, partners skills were defined and catalogued, an education schedule was created, proposed education sessions were systematically divided according to WP3 tasks and categorized (T3.1, T3.2, T3.3), a thorough analysis of existing education programs in Croatia was conducted to identify gaps and opportunities for all user categories. All the above contributed to shaping the strategic approach for digital skills and training.The indicators used to track and manage performance include feedback scores from training sessions, lectures, and events, which reflect user satisfaction. The average satisfaction score across all WP3 activities is 4.63, with an impressive score of 4.68 for the likelihood of participants recommending the trainings to others.In the current reporting period, the KPI of 2,557 participant/days has been achieved, representing 65% of the total KPI target of 3,950 participant/days. The high demand for Downstream Employee Trainings (T3.1) has led to a significant surplus, with 2,503 participant/days compared to the initial target of 2,000. This success will necessitate a review of the projected indicators for the remaining two categories of WP3 services. Digital Workforce Learning Factory (T3.2) has seen participation from 30 individuals, achieving only 2% of the planned target for the end of Year 2. This low engagement can be attributed to reduced interest and needs of ICT companies for such trainings. The Upstream Expert Training (T3.3), which focuses on knowledge exchange and best practices between experts in ICT domain of work, has seen 24 participant/days, representing 5.3% of the target set for the end of Year 2.")
        # Filter for Education
        education_keywords = [
            "Workforce downstream trainings",
            "Downstream employee training", 
            "Digital experts upstream training", 
            "Digital workforce learning factory"
        ]
        education_data = data[data['Short description of the service'].str.contains(
            '|'.join(education_keywords), case=False, na=False
        )].copy()
        education_data['Keyword'] = education_data['Short description of the service'].apply(
            lambda x: next((keyword for keyword in education_keywords if keyword.lower() in x.lower()), None)
        )

        # Ensure relevant columns are numeric
        numeric_cols = ['Content ID', 'Service price, €', 'Number of attendees']

        for col in numeric_cols:
            if col in data.columns:
                education_data[col] = pd.to_numeric(data[col], errors='coerce')  # Convert and coerce errors to NaN


        education_summary = education_data.groupby(['Start Year', 'Keyword']).agg(
            total_attendees=('Number of attendees', 'sum')
        ).reset_index()
                
        # Ensure Year is treated as a string for clean axis labels
        education_summary['Start Year'] = education_summary['Start Year'].astype(str)
        # st.write(education_summary)        
        
        # Plot for Education
        # st.write("Education Analysis")
        fig_education = px.bar(
            education_summary,
            x='Start Year',
            y='total_attendees',
            color='Keyword',
            title="Number of attendees by Delivered Education Type",
            labels={'total_attendees': 'Number of Attendees', 'Start Year': 'Year', 'Keyword': 'Training Type'},
        )
        st.plotly_chart(fig_education, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(education_summary, width=True)
            st.table(education_summary)
        
        # st.subheader("Education Analysis")

        # Filter for Training and Skills Development category
        edu_data = data[data['Service category delivered'] == "Training and skills development"]

        # Define relevant keywords in Short description of the service
        edu_keywords = [
            "Downstream employee training", 
            "Digital workforce learning factory", 
            "Workforce downstream trainings",
            "Digital experts upstream training"
        ]

        edu_filtered = data[data['Short description of the service'].str.contains(
            '|'.join(edu_keywords), case=False, na=False
        )].copy()

        edu_filtered['Education Type'] = edu_filtered['Short description of the service'].apply(
            lambda x: next((keyword for keyword in edu_keywords if keyword.lower() in x.lower()), None)
        )
        
        # st.dataframe(edu_filtered, width=True)
        
        # Ensure relevant columns are numeric
        numeric_cols = ['Service price, €', 'Number of attendees']

        for col in numeric_cols:
            if col in edu_filtered.columns:
                edu_filtered[col] = pd.to_numeric(edu_filtered[col], errors='coerce')  # Convert and coerce errors to NaN

        edu_summary = edu_filtered.groupby(["Education Type","Customer type","Short description of the service"]).agg(
            num_customers=("Customer", "nunique"),
            total_attendees=("Number of attendees", "sum"),
            total_price=("Service price, €", "sum")
        ).reset_index().sort_values(by="total_attendees", ascending=True)

        # Display Education Summary Table
        # st.write("Education Summary Table")
        # st.dataframe(edu_summary, width=True)

        # Display total attendees
        # total_attendees_edu = edu_summary["total_attendees"].sum()
        # st.write(f"### Total Attendees for Education: {total_attendees_edu}")
        # SME or PSO filter
        entity_type = st.radio("Select Entity Type:", ("SME", "Public Organization"))
        
        if entity_type == "SME":
            filtered_edu_summary = edu_summary[edu_summary['Customer type'] == "SME"]
        else:
            filtered_edu_summary = edu_summary[edu_summary['Customer type'] == "PSO"]

        # Bar Chart for Education Analysis by Service Type (Switched Axes)
        fig_edu_analysis = px.bar(
            filtered_edu_summary,
            x="total_attendees",
            y="Short description of the service",
            color="Education Type",
            title="Delivered Education by Course",
            labels={"total_attendees": "Total Attendees", "Short description of the service": "Service Type", "Education Type": "Education Type"},
            barmode="group",
            orientation='h',
            height=800
        )
        st.plotly_chart(fig_edu_analysis, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(edu_summary, width=True)
            st.table(filtered_edu_summary)

    elif analysis_type == "Bootcamp - Summary":
        st.subheader("Bootcamp - Summary")
        with st.expander("Explanation of Results"):
            st.write(" STEP RI and all project partners developed the MS5 – DIT Bootcamp Procedure operational, a bilingual (EN/HR) manual for EDIH Adria DIT Bootcamps. The open call for bootcamps was published and promoted among potential users. To date, 42 users (37 PIs and 5 SMEs) have participated in seven bootcamps, six focused on digital transformation and one on digital innovation. All project partners provided mentoring support to DIT Bootcamps beneficiaries. STEP RI and all partners also prepared the first draft of D4.2 – Digital Innovation and Transformation Bootcamps, detailing the bootcamp information.")

        # Filter for Bootcamp
        bootcamp_data = data[data['Short description of the service'].str.contains("bootcamp", case=False, na=False)].copy()
        # st.write(bootcamp_data)        
        bootcamp_summary = bootcamp_data.groupby(['Start Year','Customer']).agg(
            total_attendees=('Number of attendees', 'sum')
        ).reset_index()
    
        # Ensure Year is treated as a string for clean axis labels
        bootcamp_summary['Start Year'] = bootcamp_summary['Start Year'].astype(str)
        #st.write(bootcamp_summary,width=True)
        #st.dataframe(bootcamp_summary, width=True)

        # Plot for Bootcamp
        fig_bootcamp = px.bar(
            bootcamp_summary,
            x='Start Year',
            y='total_attendees',
            title="Bootcamp Participants by Year",
            labels={'total_attendees': 'Number of Attendees', 'Start Year': 'Year', 'Customer': 'Organization'},
        )
        st.plotly_chart(fig_bootcamp, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(bootcamp_summary, width=True)
            st.table(bootcamp_summary)

    elif analysis_type == "TBI - Summary":
        st.subheader("Test Before Invest Analysis")
        with st.expander("Explanation of Results"):
            st.write("Due to delays in aligning procedures with national rules, particularly with the Ministry of Economy, which co-finances 50% of the project activities, the preparation of the MS3 - EDIH Adria internal procedure for TBI support operations took longer than anticipated. These procedures were essential to ensure alignment with state aid rules and national implementation protocols. As a result, the final version of the EDIH Adria internal procedure for TBI support operations was officially delivered on November 16th, 2023.All project partners were actively involved in the implementation of TBIs, either by providing expert support or participating in the user acquisition and selection process.During this reporting period, EDIH Adria provided TBI support for new digital products and services to one beneficiary (30 TBI days), and TBI support for digital transformation to six beneficiaries (140 TBI days). As of the end of September 2024, a total of 895 TBI days had been contracted with 38 unique users (5 SMEs and 33 PIs).")
        # Filter for Test Before Invest category
        tbi_data = data[data['Service category delivered'] == "Test before invest"].copy()
        st.write(tbi_data)

        # Calculate mandays (Service Price / 1000)
        #tbi_data["Mandays"] = tbi_data["Service price, €"] / 1000

        # Aggregate by Customer and Status
        #tbi_summary = tbi_data.groupby(["Customer", "Status"]).agg(
        #    total_price=("Service price, €", "sum"),
        #    total_mandays=("Mandays", "sum")
        #).reset_index()

        # Display summary table
        # st.write("Test Before Invest Summary Table")
        # st.dataframe(tbi_summary, width=True)
        
        # 1. Make sure your date column is datetime
        data['Start Date'] = pd.to_datetime(data['Start Date'], dayfirst=True)

        # 2. Filter for Test Before Invest category
        tbi_data = data.loc[data['Service category delivered'] == "Test before invest"].copy()

        # 3. Define Cuttof € 1250 from Feb 1, 2025 onward
        cutoff = pd.Timestamp("2025-02-01")

        # 4. Calculate mandays (Service Price / 1000)
        #    - Before Feb 1: price / 1000
        #    - On/After Feb 1: price / 1250
        tbi_data.loc[tbi_data['Start Date'] < cutoff,  'Mandays'] = tbi_data['Service price, €'] / 1000
        tbi_data.loc[tbi_data['Start Date'] >= cutoff, 'Mandays'] = tbi_data['Service price, €'] / 1250

        # 5. Aggregate by Customer and Status
        tbi_summary = (
            tbi_data
            .groupby(['Customer', 'Status'], as_index=False)
            .agg(
                total_price=('Service price, €', 'sum'),
                total_mandays=('Mandays', 'sum')
            )
        )

        # Optional: reset index (groupby with as_index=False already did that)
        # tbi_summary = tbi_summary.reset_index(drop=True)
        # Pie Chart for Work Done by Status
        fig_pie = px.pie(
                tbi_summary,
                names="Status",
                values="total_price",
                title="Work Completion Percentage by Status",
                labels={"total_price": "Total Service Value (€)"},
                hole=0.4
        )
        st.plotly_chart(fig_pie, config={'displayModeBar': True, 'displaylogo': False})


        # Bar Chart for Service Price by Customer and Status
        fig_tbi_price = px.bar(
            tbi_summary,
            x="Customer",
            y="total_price",
            color="Status",
            title="Test Before Invest - Service Price by Customer and Status",
            labels={"total_price": "Total Service Price (€)", "Customer": "Customer"},
            barmode="group",
            height=600
        )
        st.plotly_chart(fig_tbi_price, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(tbi_summary, width=True)
            st.table(tbi_summary)
       
         # Additional Graph for Specific TBI Support Types
        tbi_keywords = [
            "TBI support - new products and services", 
            "TBI support - digital transformation", 
            "Test before invest - digital innovation", 
            "Test before invest"
        ]

        tbi_filtered = data[data['Short description of the service'].str.contains(
            '|'.join(tbi_keywords), case=False, na=False
        )].copy()

        tbi_filtered['TBI Type'] = tbi_filtered['Short description of the service'].apply(
            lambda x: next((keyword for keyword in tbi_keywords if keyword.lower() in x.lower()), None)
        )
        # Calculate mandays (Service Price / 1000)
        tbi_filtered["Mandays"] = tbi_filtered["Service price, €"] / 1000        

        tbi_type_summary = tbi_filtered.groupby(["TBI Type", "Customer"]).agg(
            total_price=("Service price, €", "sum"),
            total_mandays=("Mandays", "sum")
        ).reset_index()

        # Display TBI Type Summary Table
        # st.write("TBI Support Type Summary")
        # st.dataframe(tbi_type_summary, width=True)

        # Bar Chart for TBI Support Types by Customer
        fig_tbi_types = px.bar(
            tbi_type_summary,
            x="Customer",
            y="total_mandays",
            color="TBI Type",
            title="TBI Support Analysis by Customer",
            labels={"total_mandays": "Total Mandays", "Customer": "Customer", "TBI Type": "TBI Support Type"},
            barmode="group",
            height=600
        )
        st.plotly_chart(fig_tbi_types, config={'displayModeBar': True, 'displaylogo': False})
         
        # Count Customers per Technology Type
        tbi_tech_summary = tbi_filtered.groupby("Technology type used").agg(
            total_customers=("Customer", "nunique")
        ).reset_index().sort_values(by="total_customers", ascending=True)

        # st.subheader("TBI Customers by Technology Type")
        # st.dataframe(tbi_tech_summary, width=True)

        fig_tbi_tech = px.bar(
            tbi_tech_summary,
            x="total_customers",
            y="Technology type used",
            title="TBI Customers by Technology Type",
            labels={"total_customers": "Total Customers", "Technology type used": "Technology Type"},
            height=600
        )
        st.plotly_chart(fig_tbi_tech, config={'displayModeBar': True, 'displaylogo': False})
    
    elif analysis_type == "DAP&FCO - Summary":
        st.subheader("DAP & FCO Analysis")
        with st.expander("Explanation of Results"):
            st.write("ENT and STEP RI, in collaboration with all partners, developed the MS6 – DAP & FCO Assessment Formats document, which defines DAP and FCO content and methodology. The open call for investment support has been published and promoted. As of September 2024, two users (one SME and one PI) have contracted the development of DAPs and FCOs. The DAP & FCO process follows TBI and bootcamp activities, so users must complete TBI or bootcamp before starting DAP or FCO creation. As a result, fewer DAPs and FCOs have been completed to date, but a higher number is expected as more TBI activities are finalized")
        # Filter for Test Before Invest category
        dap_data = data[data['Service category delivered'] == "Support to find investment"].copy()
        # st.write(tbi_data)

        # Calculate mandays (Service Price / 1000)
        dap_data["Mandays"] = dap_data["Service price, €"] / 1000

        # Aggregate by Customer and Status
        dap_summary = dap_data.groupby(["Customer", "Status"]).agg(
            total_price=("Service price, €", "sum"),
            total_mandays=("Mandays", "sum")
        ).reset_index()

        # Display summary table
        # st.write("DAP & FCO Summary Table")
        # st.dataframe(dap_summary, width=True)

        # Bar Chart for Service Price by Customer and Status
        fig_dap_price = px.bar(
            dap_summary,
            x="Customer",
            y="total_price",
            color="Status",
            title="DAP & FCO - Service value by Customer and Status",
            labels={"total_price": "Total Service Price (€)", "Customer": "Customer"},
            barmode="group",
            height=600
        )
        st.plotly_chart(fig_dap_price, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(dap_summary, width=True)
            st.table(dap_summary)
       
         # Additional Graph for Specific TBI Support Types
        tbi_keywords = [
            "DAP - digitalisation action plan", 
            "FCO assessment", 
            "Digital transformation project" 
        ]

        tbi_filtered = data[data['Short description of the service'].str.contains(
            '|'.join(tbi_keywords), case=False, na=False
        )].copy()

        tbi_filtered['DAP&FCO Type'] = tbi_filtered['Short description of the service'].apply(
            lambda x: next((keyword for keyword in tbi_keywords if keyword.lower() in x.lower()), None)
        )
        # Calculate mandays (Service Price / 1000)
        tbi_filtered["Mandays"] = tbi_filtered["Service price, €"] / 1000        

        tbi_type_summary = tbi_filtered.groupby(["DAP&FCO Type", "Customer"]).agg(
            total_price=("Service price, €", "sum"),
            total_mandays=("Mandays", "sum")
        ).reset_index()

        # Display TBI Type Summary Table
        # st.write("TBI Support Type Summary")
        # st.dataframe(tbi_type_summary, width=True)

        # Bar Chart for TBI Support Types by Customer
        fig_tbi_types = px.bar(
            tbi_type_summary,
            x="Customer",
            y="total_mandays",
            color="DAP&FCO Type",
            title="DAP&FCO Support Analysis by Customer",
            labels={"total_mandays": "Total Mandays", "Customer": "Customer", "DAP&FCO Type": "DAP&FCO Support Type"},
            barmode="group",
            height=600
        )
        st.plotly_chart(fig_tbi_types, config={'displayModeBar': True, 'displaylogo': False})
         
        # Count Customers per Technology Type
        tbi_tech_summary = tbi_filtered.groupby("Technology type used").agg(
            total_customers=("Customer", "nunique")
        ).reset_index().sort_values(by="total_customers", ascending=True)

        # st.subheader("TBI Customers by Technology Type")
        # st.dataframe(tbi_tech_summary, width=True)

        fig_tbi_tech = px.bar(
            tbi_tech_summary,
            x="total_customers",
            y="Technology type used",
            title="DAP&FCO Customers by Technology Type",
            labels={"total_customers": "Total Customers", "Technology type used": "Technology Type"},
            height=600
        )
        st.plotly_chart(fig_tbi_tech, config={'displayModeBar': True, 'displaylogo': False})

    elif analysis_type == "State Aid - Summary":
        # Podaci iz Teams tablica!
        # Convert numeric columns to proper format
        numeric_columns_ps = ["Vrijednost usluge"]
        numeric_columns_sme = ["Vrijednost usluge", "Iznos potpore"]

        for col in numeric_columns_ps:
            ps_data[col] = pd.to_numeric(ps_data[col], errors='coerce')

        for col in numeric_columns_sme:
            sme_data[col] = pd.to_numeric(sme_data[col], errors='coerce')

        # Public Sector Analysis
        ps_summary = ps_data.groupby(['Vrsta usluge', 'Započeto je pružanje usluge (DA/NE)']).agg(
            total_value=('Vrijednost usluge', 'sum')
        ).reset_index()
        
        st.subheader("State Aid Summary")
        # st.dataframe(ps_summary, width=True)
        
        fig_ps = px.bar(
            ps_summary,
            x='Vrsta usluge',
            y='total_value',
            color='Započeto je pružanje usluge (DA/NE)',
            title='State Aid Summary for Public Sector',
            labels={'total_value': 'Total Value (€)', 'Vrsta usluge': 'Service Type'},
            barmode='group'
        )
        st.plotly_chart(fig_ps, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(ps_summary, width=True)
            st.table(ps_summary)
        
        # SME Analysis
        sme_summary = sme_data.groupby(['Vrsta usluge', 'Započeto je pružanje usluge (DA/NE)']).agg(
            total_value=('Vrijednost usluge', 'sum'),
            total_support=('Iznos potpore', 'sum')
        ).reset_index()
        
        # st.subheader("SME - State Aid Summary")
        # st.dataframe(sme_summary, width=True)

        fig_sme = px.bar(
            sme_summary,
            x='Vrsta usluge',
            y=['total_value', 'total_support'],
            color='Započeto je pružanje usluge (DA/NE)',
            title='State Aid Summary for SMEs',
            labels={'value': 'Total (€)', 'Vrsta usluge': 'Service Type'},
            barmode='group'
        )
        st.plotly_chart(fig_sme, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(sme_summary, width=True)
            st.table(sme_summary)      

        # Podaci iz EU Site
        state_aid_summary = data.groupby('Specific information on State Aid').agg(
            total_services=('Content ID', 'count'),
            total_aid=('Amount of the service price to be reported as Aid of national or regional public nature, €', 'sum')
        ).reset_index().sort_values(by='total_aid', ascending=False)
        # st.subheader("State Aid Summary")
        # st.write(state_aid_summary)
        fig = px.bar(
            state_aid_summary,
            x='Specific information on State Aid',
            y='total_services',
            title='State Aid Summary',
            labels={'total_services': 'Number of Services', 'Specific information on State Aid': 'State Aid'},
            text='total_services'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, config={'displayModeBar': True, 'displaylogo': False})
        with st.expander("Tabular data"):    
            # st.dataframe(state_aid_summary, width=True)
            st.table(state_aid_summary)  


    elif analysis_type == "ESG - Summary":
        st.subheader("ESG Analytics by Organisation")

        dataset_type = st.radio("Select Dataset:", ("SMEs", "Public Organizations"))
        
        if dataset_type == "SMEs":
            selected_data = data_smea
            org_column = "SME name"
            env_col = "Green Digitalisation"
            soc_cols = ["Digital Business Strategy", "Digital Readiness", "Human-Centric Digitalisation"]
            gov_cols = ["Data Governance", "Automation & Artificial Intelligence"]
        else:
            selected_data = data_psoa
            org_column = "PSO name"
            env_col = "Green Digitalisation"
            soc_cols = ["Digital Strategy and Investments", "Digital Readiness", "Human-Centric Digitalisation"]
            gov_cols = ["Data Management and Security", "Interoperability"]

        if org_column in selected_data.columns:
            selected_data["Environment"] = selected_data[env_col]
            selected_data["Society"] = selected_data[soc_cols].mean(axis=1)
            selected_data["Governance"] = selected_data[gov_cols].mean(axis=1)

            esg_summary = selected_data[[org_column, "Environment", "Society", "Governance"]].dropna()
            esg_summary.set_index(org_column, inplace=True)

            fig_esg_heatmap = px.imshow(
                esg_summary,
                labels=dict(x="ESG Category", y="Organisation", color="Score"),
                x=["Environment", "Society", "Governance"],
                y=esg_summary.index,
                color_continuous_scale=px.colors.sequential.Blues,
                title="ESG Score Heatmap",
                height=900,
                width=900,
                aspect="auto"
            )
            st.plotly_chart(fig_esg_heatmap, config={'displayModeBar': True, 'displaylogo': False})


    elif analysis_type == "DMA - Summary":
        st.subheader("DMA Analytics by Organisation")
        with st.expander("Explanation of Results"):
            st.write("Digital Maturity Assessments (DMA) are crucial for the project, serving not only as a precursor to TBI activities but also as a foundation for identifying additional tailored services, even for users who may not opt for TBI. A total of 83 DMAs have been conducted to date (38% of the planned 220), comprising 32 SMEs and 51 Public Institutions (PIs), all at the T0 stage. Ericsson Nikola Tesla, University of Rijeka, and University of Pula have primarily led the DMA process, with all partners contributing. These assessments are outlined in D.4.1 – Digital Maturity Assessment (DMA) and Audits, prepared under the leadership of RDA Porin (ex Smart RI) and Ericsson Nikola Tesla.")

        # User selects dataset
        dataset_type = st.radio("Select Dataset:", ("SMEs", "Public Organizations"))
        
        if dataset_type == "SMEs":
            selected_data = data_smea
            
            org_column = "SME name"
            pdf_folder = app_folder + "/DMA/SME"
            json_folder = app_folder + "/DMA/SME/JSON"
            with st.container():
                cola, colb, colc = st.columns(3)
                with cola:
                    st.metric("Digital Bussines Strategy (%):", value=int(selected_data["Digital Business Strategy"].mean()), delta=100, border=True)
                    st.metric("Data Governance (%):", value=int(selected_data["Data Governance"].mean()), delta=100, border=True)
                with colb:
                    st.metric("Digital Readines (%):", value=int(selected_data["Digital Readiness"].mean()), delta=100, border=True)
                    st.metric("Artificial Intelligence (%):", value=int(selected_data["Automation & Artificial Intelligence"].mean()), delta=100, border=True)
                with colc:
                    st.metric("Human Centric Digitalisation (%):", value=int(selected_data["Human-Centric Digitalisation"].mean()), delta=100, border=True)
                    st.metric("Green Digitalisation (%):", value=int(selected_data["Green Digitalisation"].mean()), delta=100, border=True)
        else:
            selected_data = data_psoa

            org_column = "PSO name"
            pdf_folder = app_folder + "/DMA/PSO"
            json_folder = app_folder + "/DMA/PSO/JSON"
            with st.container():
                cola, colb, colc = st.columns(3)
                with cola:
                    st.metric("Digital Strategy & Investments (%):", value=int(selected_data["Digital Strategy and Investments"].mean()), delta=100, border=True)
                    st.metric("Data Management & Security (%):", value=int(selected_data["Data Management and Security"].mean()), delta=100, border=True)
                with colb:
                    st.metric("Digital Readiness (%):", value=int(selected_data["Digital Readiness"].mean()), delta=100, border=True)
                    st.metric("Interoperability (%):", value=int(selected_data["Interoperability"].mean()), delta=100, border=True)
                with colc:
                    st.metric("Human Centric Digitalisation (%):", value=int(selected_data["Human-Centric Digitalisation"].mean()), delta=100, border=True)
                    st.metric("Green Digitalisation (%):", value=int(selected_data["Green Digitalisation"].mean()), delta=100, border=True)

        # Clean column names
        selected_data.columns = selected_data.columns.str.replace('"', '').str.strip()
        full_data = selected_data.copy()  # čuva sve kolone

        # Extract dimensions for the radar chart (between DMA Score and EDIH name)
        dma_start_col = selected_data.columns.get_loc("DMA Score")
        dma_end_col = selected_data.columns.get_loc("EDIH Name")
        dma_columns = selected_data.columns[dma_start_col + 1 : dma_end_col]

        # Extract relevant DMA score columns
        dma_score_columns = [col for col in selected_data.columns if "DMA Score" in col]

        if org_column in selected_data.columns:
            organization_names = selected_data[org_column].dropna().unique()
            
            # --- 1️⃣ DMA Heatmap ---
            heatmap_data = selected_data.set_index(org_column)[dma_columns]
            heatmap_data = heatmap_data.dropna()

            fig_heatmap = go.Figure()

            fig_heatmap.add_trace(go.Heatmap(
                z=heatmap_data.values,  # Data values
                x=heatmap_data.columns,  # X-axis labels (Organizations)
                y=heatmap_data.index,  # Y-axis labels (Dimensions)
                colorscale="RdBu",
                colorbar=dict(title="Rating")
            ))

            annotations = []
            for i, col in enumerate(heatmap_data.columns):
                annotations.append(
                    dict(
                        x=i, 
                        y=len(heatmap_data.index) + 4,  # Position slightly above the heatmap
                        text=col, 
                        showarrow=False,
                        font=dict(size=12, color="lightgray"),
                        textangle=45
                    )
                )

            fig_heatmap.update_layout(
                title="DMA Score Heatmap",
                height=1200,
                width=900,
                xaxis=dict(
                    title="Organisation",
                    side="bottom",
                    tickmode="array",
                    tickvals=list(range(len(heatmap_data.columns))),
                    ticktext=heatmap_data.columns
                ),
                yaxis=dict(title="Dimensions"),
                annotations=annotations
            )

            st.plotly_chart(fig_heatmap, config={'displayModeBar': True, 'displaylogo': False})

     
        # st.subheader("📁 DMA dokumenti po organizaciji (T0 / T1 / T2)")

        # --- 1️⃣ Funkcija za pregled PDF-ova po organizaciji ---
        @st.cache_data(show_spinner=False)
        def list_dma_pdfs_by_type(base_dirs):
            """Pregled dostupnih DMA PDF-ova za SME i PSO organizacije."""
            all_results = []
            for org_type, folder in base_dirs.items():
                if not os.path.exists(folder):
                    continue

                pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
                records = {}

                for f in pdf_files:
                    name = f.replace(".pdf", "")
                    # Prepoznaj oznaku (T0, T1, T2)
                    parts = name.split()
                    label = next((p for p in parts if p.upper() in ["T0", "T1", "T2"]), None)
                    org_name = name.replace(label if label else "", "").strip()

                    if org_name not in records:
                        records[org_name] = {"Type": org_type, "T0": "❌", "T1": "❌", "T2": "❌"}
                    if label:
                        records[org_name][label.upper()] = "✅"

                # Konverzija u DataFrame
                for org, data in records.items():
                    all_results.append({
                        "Type": data["Type"],
                        "Organization": org,
                        "T0": data["T0"],
                        "T1": data["T1"],
                        "T2": data["T2"],
                    })

            if not all_results:
                return pd.DataFrame(columns=["Type", "Organization", "T0", "T1", "T2"])
            return pd.DataFrame(all_results).sort_values(by=["Type", "Organization"]).reset_index(drop=True)


        # --- 2️⃣ Učitaj i filtriraj ---
        dma_overview_df = list_dma_pdfs_by_type(CATEGORIES)
        st.write(f"📄 Ukupno realiziranih DMA: **{len(dma_overview_df)}**")
        show_missing = st.checkbox("🔍 Prikaži samo nepotpune organizacije")      

        if show_missing and not dma_overview_df.empty:
            mask = (dma_overview_df["T0"] == "❌") | (dma_overview_df["T1"] == "❌") | (dma_overview_df["T2"] == "❌")
            dma_overview_df = dma_overview_df[mask]

        # --- 3️⃣ Izračun statistike ---
        if not dma_overview_df.empty:
            stats = (
                dma_overview_df
                .groupby("Type")[["T0", "T1", "T2"]]
                .apply(lambda x: (x == "✅").sum())
                .reset_index()
            )

            total_counts = dma_overview_df.groupby("Type").size().reset_index(name="Total")
            stats = stats.merge(total_counts, on="Type")

            st.markdown("### 📊 Statistika po tipu organizacije")

            for _, row in stats.iterrows():
                complete = (row["T0"] + row["T1"] + row["T2"]) / (row["Total"] * 3) * 100
                st.write(
                    f"**{row['Type']}** — Ukupno: {int(row['Total'])} | "
                    f"T0: {int(row['T0'])} | T1: {int(row['T1'])} | T2: {int(row['T2'])} | "
                    f"✅ Potpuno popunjeni: {complete:.1f}%"
                )

        # --- 4️⃣ Prikaz tablice ---
        if not dma_overview_df.empty:
            with st.expander("### 📋 Pregled DMA dokumenata"):
            # st.markdown("### 📋 Pregled DMA dokumenata")
            # st.dataframe(dma_overview_df, width=stretch, hide_index=True)
                st.table(dma_overview_df)
        else:
            st.warning("⚠️ Nema pronađenih PDF-ova u zadanim folderima.")

        # --- 5️⃣ Export u Excel ---
        if not dma_overview_df.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                dma_overview_df.to_excel(writer, index=False, sheet_name="DMA Overview")
            output.seek(0)

            st.download_button(
                label="💾 Preuzmi Excel izvještaj",
                data=output,
                file_name="dma_overview.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        

            st.subheader("📊 Detaljni pregled organizacije")

            organization_name = st.selectbox(
                "Odaberi organizaciju:",
                sorted(organization_names)
            )
           
            org_records = full_data[full_data[org_column] == organization_name]
            # st.dataframe(org_records, use_container_width=True)
            # org_records = selected_data[selected_data[org_column] == organization_name]

            if org_records.empty:
                st.warning("⚠️ Nema dostupnih DMA zapisa za ovu organizaciju.")
            else:
                if "DMA Timing" not in org_records.columns:
                    st.error("Kolona 'DMA Timing' nije pronađena u datasetu.")
                else:
                    # Prepoznaj sve numeričke metrike osim identificirajućih kolona
                    skip_cols = [org_column, "DMA Timing", "EDIH Name", "DMA Score", "SME ID", "PSO ID"]
                    metric_cols = [
                        c for c in org_records.columns
                        if c not in skip_cols and org_records[c].dtype in [int, float]
                    ]

                    fig_radar = go.Figure()

                    # Faze DMA (T0, T1, T2)
                    available_timings = org_records["DMA Timing"].dropna().unique()

                    for stage in ["T0", "T1", "T2"]:
                        if stage in available_timings:
                            stage_row = org_records[org_records["DMA Timing"] == stage].iloc[0]
                            values = [stage_row[c] for c in metric_cols]
                            fig_radar.add_trace(go.Scatterpolar(
                                r=values,
                                theta=metric_cols,
                                fill='toself',
                                name=stage
                            ))

                    fig_radar.update_layout(
                        title=f"Digital Maturity Progression – {organization_name}",
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=True,
                        template="plotly_white"
                    )

                    st.plotly_chart(fig_radar, config={'displayModeBar': True, 'displaylogo': False})

                    # Opcionalno: prikaži sirove podatke
                    with st.expander("📋 Pogledaj tablične rezultate"):
                        st.dataframe(org_records, use_container_width=True)


            # ---- Add PDF Display Logic ----
            st.subheader("📄 Detailed DMA Report")

            # Pronađi sve PDF-ove koji sadrže naziv organizacije (neovisno o velikim/malim slovima)
            pdf_files = [
                f for f in os.listdir(pdf_folder)
                if organization_name.lower() in f.lower() and f.lower().endswith(".pdf")
            ]

            if pdf_files:
                # Sortiraj prema DMA oznaci ako postoji (T0, T1, T2)
                pdf_files = sorted(pdf_files, key=lambda x: ("T0" in x, "T1" in x, "T2" in x), reverse=True)

                # Pokaži korisniku koje su datoteke pronađene
                st.markdown(f"Pronađeni izvještaji za **{organization_name}**:")
                for f in pdf_files:
                    st.markdown(f"- {f}")

                # Omogući odabir konkretne verzije (T0 / T1 / T2)
                selected_pdf = st.selectbox(
                    "📑 Odaberi DMA izvještaj:",
                    pdf_files,
                    format_func=lambda x: os.path.splitext(x)[0]  # prikazuje bez ekstenzije
                )

                pdf_path = os.path.join(pdf_folder, selected_pdf)

                # --- Akcije korisnika ---

                if st.button("👁️ Prikaži PDF izvještaj"):
                    st.write(f"Prikazujem detaljni PDF izvještaj: `{selected_pdf}`")
                    st.pdf(pdf_path, height=800)

                if st.button("🧠 AI sažetak izvještaja"):
                    with st.spinner(f"AI analizira {selected_pdf}..."):
                        summary_text = get_summary(organization_name)
                    st.subheader("📝 Sažetak izvještaja")
                    st.write(summary_text)

            else:
                st.warning(f"⚠️ Nije pronađen nijedan PDF izvještaj za **{organization_name}**.")




# Right sidebar section
with col2:
    st.subheader("Progress Toward Target")
    # Add Gauge for Targets
    if analysis_type == "EDIH ADRIA Service Overview":
        # st.subheader("Service Summary with Target")

        # Example: Total Revenue Target
        total_revenue = data['Service price, €'].sum()
        target_revenue = 2_645_000  # € target

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_revenue,
            delta={'reference': target_revenue, 'position': "top"},
            gauge={
                'axis': {'range': [0, target_revenue]},
                'bar': {'color': "orange"},
                'steps': [
                    {'range': [0, target_revenue * 0.5], 'color': "lightgray"},
                    {'range': [target_revenue * 0.5, target_revenue], 'color': "yellow"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_revenue *0.9
                }
            },
            title={'text': "Total Revenue (€)"}
        ))

        st.plotly_chart(fig_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Total partner cost - midterm (€):", value=1128186.17, delta=2645000, border=True) 
    
    elif analysis_type == "EU EDIH Comparison":
        
        # Filter for the 4 specific EDIHs
        selected_edihs = ["EDIH Adria", "CROBOHUBplusplus", "AI and Gaming EDIH", "AI4HEALTH.Cro"]
        filtered_ranking = ranking_summary [ranking_summary ["EDIH Name"].isin(selected_edihs)]
        # st.dataframe(filtered_ranking, width=True)
        for index, row in filtered_ranking.iterrows():
            st.metric(label=row["EDIH Name"], value=row["DMA"] + row["TBI"] + row["EDUC"] + row["FCO"] + row["NETWORK"], border=True)
                
        # st.metric("Number of organisations with completed DMA:", value=total_customers, delta=target_customers, border=True)     
    
    elif analysis_type == "Bootcamp - Summary":
        # bootcamp_data['Customer'] = bootcamp_data['Customer'].astype(str).str.strip().str.lower()        
        total_customers = len(bootcamp_data)
        target_customers = 85
        
        # Calculate percentage of the target achieved
        percentage_achieved = (total_customers / target_customers) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_customers, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "Target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)
        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Number of organisations with completed bootcamp:", value=total_customers, delta=target_customers, border=True)
 
    elif analysis_type == "DAP&FCO - Summary":
        # bootcamp_data['Customer'] = bootcamp_data['Customer'].astype(str).str.strip().str.lower()        
        total_customers = len(dap_data)
        target_customers = 50
        
        # Calculate percentage of the target achieved
        percentage_achieved = (total_customers / target_customers) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_customers, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "Target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)
        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Number of organisations with DAP&FCO:", value=total_customers, delta=target_customers, border=True) 


    elif analysis_type == "DMA - Summary":
        
        if apply_reporting_filter:        
            total_customers = 83
            target_customers = 120
        else:
            total_customers = data_smea['SME name'].nunique() + data_psoa['PSO name'].nunique()
            target_customers = 120   

        
        # Calculate percentage of the target achieved
        percentage_achieved = (total_customers / target_customers) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_customers, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "DMA target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)
        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Number of organisations with completed DMA:", value=total_customers, delta=target_customers, border=True)     
    
    elif analysis_type == "TBI - Summary":
        
        if apply_reporting_filter:        
            total_mandays = 895
            target_mandays = 1400
            total_organisations = len(tbi_summary["total_mandays"])
        else:
            total_mandays = int(tbi_summary["total_mandays"].sum())
            target_mandays = 1400
            total_organisations = len(tbi_summary["total_mandays"])

        # Calculate percentage of the target achieved
        percentage_achieved = (total_mandays / target_mandays) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_mandays, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "TBI target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)
        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Number contracted TBI days:", value=total_mandays, delta=target_mandays, border=True)
        st.metric("Number of organisations:", value=total_organisations, delta=70, border=True)

    elif analysis_type == "State Aid - Summary":
        
        if apply_reporting_filter:        
            total_budget= 881300
            target_budget = 1322500
        else:
            total_budget = int(state_aid_summary["total_aid"].sum())
            target_budget = 1322500 

        # Calculate percentage of the target achieved
        percentage_achieved = (total_budget / target_budget) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_budget, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "TBI target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)

        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("State aid (€):", value=total_budget, delta=target_budget, border=True)
        st.metric("Issued decisions:", value=73, delta=100, border=True)
        st.metric("Issued statements:", value=250, delta=500, border=True)
        
    elif analysis_type == "Education - Summary":
        # 1.kategorija - Workforce downstream trainings        
        
        if apply_reporting_filter:        
            total_workforce = 2503
            target_workforce = 2000
        else:
            workforce_train1 = edu_summary[edu_summary["Education Type"] == "Workforce downstream trainings"]
            workforce_train2 = edu_summary[edu_summary["Education Type"] == "Downstream employee training"]
            total_workforce = int(workforce_train1["total_attendees"].sum()) + int(workforce_train2["total_attendees"].sum())
            target_workforce = 3000 
        
        # 2.kategorija - Digital Workforce learning factory 
        workforce_learning = edu_summary[edu_summary["Education Type"] == "Digital workforce learning factory"]
        total_factroy= int(workforce_learning["total_attendees"].sum())
        target_factroy = 250

        
        # 3. kategorija - Digital experts upstream training
        workforce_downstream = edu_summary[edu_summary["Education Type"] == "Digital experts upstream training"]
        total_downstream= int(workforce_downstream["total_attendees"].sum())
        target_downstream = 330


        # Calculate percentage of the target achieved
        total_edu = total_workforce + total_factroy + total_downstream
        target_edu=  target_workforce + target_factroy + target_downstream
        percentage_achieved = (total_edu / target_edu) * 100

        fig_bootcamp_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentage_achieved,
            delta={'reference': target_edu, 'position': "top"},
            gauge={
                'axis': {'range': [0, 100],'tickcolor': "lightgray"},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "orange"},
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            },
            title={'text': "EDU target achieved in %"}
        ))
        fig_bootcamp_gauge.update_layout(font = {'family': "Arial"}, height=300)
        st.plotly_chart(fig_bootcamp_gauge, config={'displayModeBar': True, 'displaylogo': False})
        st.metric("Workforce downstream trainings:", value=total_workforce, delta=target_workforce, border=True)   
        st.metric("Digital Workforce learning factory:", value=total_factroy, delta=target_factroy, border=True)
        st.metric("Digital experts upstream training:", value=total_downstream, delta=target_downstream, border=True)
        st.metric("The average satisfaction:", value=4.63, delta=5, border=True)
        st.metric("Participants recommending the trainings to others:", value=4.68, delta=5, border=True)
        
        edu_sme = edu_filtered[edu_filtered['Customer type'] == "SME"]
        total_edu_sme= edu_sme["Customer"].nunique()
        #st.write("Columns in edu_sme:", edu_sme.columns.tolist())
        # total_edu_sme = edu_sme.groupby("Customer")["Customer"].nunique().count()        
        st.metric("SME organisations participating:", value=total_edu_sme, delta=100, border=True)

        edu_pso = edu_filtered[edu_filtered['Customer type'] == "PSO"]
        total_edu_pso= edu_pso["Customer"].nunique()
        #total_edu_pso = edu_pso.groupby("Customer")["Customer"].nunique().count()          
        st.metric("PSO organisations participating:", value=total_edu_pso, delta=100, border=True)
        


# Footer
# st.sidebar.info("EDIH ADRIA KPI Dashboard - KPIs will be continuously monitored to track progress, identify, and solve issues and adjust accordingly")
st.sidebar.info("EDIH EU Data sync: 15.10.2025")
# st.sidebar.warning("AI RAG Engine by Syntagent - UNIRI spin-off")
# st.sidebar.image(app_folder + "/Slike/SyntAgent-red.png", width=250)
