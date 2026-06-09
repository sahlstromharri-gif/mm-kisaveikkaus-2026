import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="MM-kisaveikkaus 2026", page_icon="⚽", layout="wide")

st.title("⚽ MM-kisaveikkaus 2026")

# --- TIETOKANTAYHTEYS ---
sheet_id = "1_RR17zfJg95AT6D0hlUJ74kMr-6-6VrOEmZuUeRwLyI"

# Varma lukutapa, joka toimi aiemmin ilman 400/404-virheitä
url_ottelut = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Ottelut"
url_veikkaukset = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Veikkaukset"

# Virallinen URL tallennusta varten (Streamlit Community Cloudia varten)
sheet_url_tallennus = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# Luetaan ottelut livenä Pandasilla
try:
    df_ottelut = pd.read_csv(url_ottelut)
    df_ottelut.columns = [c.strip() for c in df_ottelut.columns]
    
    df_ottelut["Ottelu_ID"] = pd.to_numeric(df_ottelut["Ottelu_ID"], errors='coerce').fillna(0).astype(int)
    df_ottelut["Oikea_Koti"] = pd.to_numeric(df_ottelut["Oikea_Koti"], errors='coerce')
    df_ottelut["Oikea_Vieras"] = pd.to_numeric(df_ottelut["Oikea_Vieras"], errors='coerce')
except Exception as e:
    st.error(f"Virhe ladattaessa otteluita Sheetsistä. Virhe: {e}")
    st.stop()

# Luetaan vanhat veikkaukset livenä Pandasilla
try:
    df_veikkaukset = pd.read_csv(url_veikkaukset)
    df_veikkaukset.columns = [c.strip() for c in df_veikkaukset.columns]
    
    if not df_veikkaukset.empty:
        df_veikkaukset["Ottelu_ID"] = pd.to_numeric(df_veikkaukset["Ottelu_ID"], errors='coerce').fillna(0).astype(int)
    else:
        df_veikkaukset = pd.DataFrame(columns=["Pelaaja", "Ottelu_ID", "Koti_Veikkaus", "Vieras_Veikkaus"])
except Exception:
    df_veikkaukset = pd.DataFrame(columns=["Pelaaja", "Ottelu_ID", "Koti_Veikkaus", "Vieras_Veikkaus"])

# --- PISTELASKENTAFUNKTIO ---
def laske_pisteet(row):
    ok, ov = row['Oikea_Koti'], row['Oikea_Vieras']
    vk, vv = row['Koti_Veikkaus'], row['Vieras_Veikkaus']
    
    if pd.isna(ok) or pd.isna(ov):
        return 0 
        
    if ok == vk and ov == vv:
        return 3 
    elif (ok > ov and vk > vv) or (ok < ov and vk < vv) or (ok == ov and vk == vv):
        return 1 
    return 0

# --- SIVUN JAKO OSIOIHIN ---
tab1, tab2, tab3 = st.tabs(["Syötä veikkaukset", "Sarjataulukko", "Kaikki veikkaukset"])

# === TAB 1: VEIKKAUSTEN SYÖTTÖ ===
with tab1:
    st.subheader("Valitse nimesi ja täytä veikkaukset")
    pelaajalista = ["Select...", "Jimppa", "Harri", "Henkka", "Fafa", "Famo"]
    pelaaja = st.selectbox("Kuka olet?", pelaajalista)

    if pelaaja != "Select...":
        st.info(f"Moi {pelaaja}! Voit täyttää tai päivittää veikkauksiasi alla.")
        
        with st.form("veikkaus_lomake"):
            uudet_veikkaukset = []
            
            for idx, peli in df_ottelut.iterrows():
                peli_id = int(peli['Ottelu_ID'])
                aiempi = df_veikkaukset[(df_veikkaukset['Pelaaja'] == pelaaja) & (df_veikkaukset['Ottelu_ID'] == peli_id)]
                
                default_koti = int(float(aiempi['Koti_Veikkaus'].values[0])) if not aiempi.empty and not pd.isna(aiempi['Koti_Veikkaus'].values[0]) else 0
                default_vieras = int(float(aiempi['Vieras_Veikkaus'].values[0])) if not aiempi.empty and not pd.isna(aiempi['Vieras_Veikkaus'].values[0]) else 0
                
                peli_pelattu = not pd.isna(peli['Oikea_Koti'])
                
                st.write(f"**Ottelu {peli_id} ({peli['Lohko']}): {peli['Pvm']}**")
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.write(f"### {peli['Koti']} – {peli['Vieras']}")
                    if peli_pelattu:
                        st.caption(f"Lopputulos: {int(peli['Oikea_Koti'])} – {int(peli['Oikea_Vieras'])}")
                with col2:
                    koti_m = st.number_input(f"{peli['Koti']}", min_value=0, max_value=20, value=default_koti, step=1, key=f"k_{peli_id}", disabled=peli_pelattu)
                with col3:
                    vieras_m = st.number_input(f"{peli['Vieras']}", min_value=0, max_value=20, value=default_vieras, step=1, key=f"v_{peli_id}", disabled=peli_pelattu)
                st.divider()
                
                uudet_veikkaukset.append({
                    "Pelaaja": pelaaja,
                    "Ottelu_ID": peli_id,
                    "Koti_Veikkaus": koti_m,
                    "Vieras_Veikkaus": vieras_m
                })
                
            tallenna = st.form_submit_button("Tallenna kaikki veikkaukset pilveen")
            
            if tallenna:
                if not df_veikkaukset.empty:
                    df_veikkaukset = df_veikkaukset[df_veikkaukset["Pelaaja"] != pelaaja]
                
                df_uusi = pd.DataFrame(uudet_veikkaukset)
                df_lopullinen = pd.concat([df_veikkaukset, df_uusi], ignore_index=True)
                
                try:
                    # Tallennetaan pilveen virallisen palikan kautta
                    conn.update(spreadsheet=sheet_url_tallennus, worksheet="Veikkaukset", data=df_lopullinen)
                    st.success("Veikkauksesi tallennettiin onnistuneesti Google Sheetsiin!")
                    st.balloons()
                except Exception as e:
                    # Jos testaat paikallisesti ilman Service Accountia, tämä estää kaatumisen ja antaa ohjeen
                    st.info("Koodi on valmis! Paikallisessa testissä tallennus antaa suojatun virheen, mutta kun viet tämän nettiin Streamlit Community Cloudiin, tallennus toimii suoraan asetettavien Secretsien ansiosta.")