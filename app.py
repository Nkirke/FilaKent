import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Opsætning af siden + mobil-app meta tags
st.set_page_config(page_title="FILAKENT", layout="centered")

st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="FILAKENT">
    <meta name="mobile-web-app-capable" content="yes">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&display=swap');

    .viltrum-header {
        font-family: 'Archivo Black', Impact, sans-serif;
        font-size: 3.6rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: -2px;
        line-height: 1.0;
        color: #FFFFFF;
        margin-bottom: 0.2rem;
        text-shadow: 3px 3px 0px #E53935;
    }
    .viltrum-sub {
        font-size: 0.9rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #9CA3AF;
        margin-bottom: 1.2rem;
        font-weight: 600;
    }
    /* Gør knapper og inputfelter lidt større og nemmere at ramme med tommelfingeren */
    .stButton button {
        min-height: 48px;
        font-weight: 600;
    }
    </style>
    <div class="viltrum-header">FILAKENT</div>
    <div class="viltrum-sub">Filament Lagerstyring</div>
    """,
    unsafe_allow_html=True,
)

# INDSÆT DIT FORMSPREE-LINK HERUNDER:
FORMSPREE_URL = "https://formspree.io/f/maeonjez"

MATERIALER = ["PLA", "PETG", "ABS", "ASA", "TPU", "Andet"]
FARVER = [
    "Sort",
    "Hvid",
    "Grå",
    "Blå",
    "Rød",
    "Grøn",
    "Gul",
    "Orange",
    "Lyserød",
    "Gennemsigtig",
    "Andet",
]
BRANDS = ["Bambu Lab", "Jayo", "Andet"]
PLACERINGER = ["Hylde", "Varmeskab"]

# Forbindelse til Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


def indlaes_data():
    df = conn.read(ttl=0)
    if df.empty or "ID" not in df.columns:
        return pd.DataFrame(
            columns=[
                "ID",
                "Materiale",
                "Farve",
                "Detalje",
                "Brand",
                "Vaegt_g",
                "Placering",
            ]
        )
    df = df.dropna(how="all")
    df["Detalje"] = df["Detalje"].fillna("")
    df["ID"] = df["ID"].astype(int)
    df["Vaegt_g"] = df["Vaegt_g"].astype(int)
    return df


def gem_data(df):
    df = df.reset_index(drop=True)
    if not df.empty:
        df["ID"] = range(1, len(df) + 1)
    conn.update(data=df)


df = indlaes_data()

tab_soeg, tab_lager, tab_tilfoej, tab_feedback = st.tabs(
    ["🔍 Søg", "📦 Lager", "➕ Tilføj", "💬 Feedback"]
)

# --- FANE 1: SØG ---
with tab_soeg:
    st.subheader("Hvad skal du printe med?")

    col1, col2 = st.columns(2)
    with col1:
        soeg_materiale = st.selectbox("Materiale", ["Alle"] + MATERIALER)
    with col2:
        soeg_farve = st.selectbox("Farve", ["Alle"] + FARVER)

    aktivt_lager = df[df["Vaegt_g"] > 0] if not df.empty else df

    if soeg_materiale != "Alle" and soeg_farve != "Alle":
        direkte_match = aktivt_lager[
            (aktivt_lager["Materiale"] == soeg_materiale)
            & (aktivt_lager["Farve"] == soeg_farve)
        ]

        if not direkte_match.empty:
            st.success(
                f"Fundet! Du har {len(direkte_match)} rulle(r) med {soeg_farve} {soeg_materiale}:"
            )
            st.dataframe(
                direkte_match[
                    ["ID", "Materiale", "Farve", "Detalje", "Brand", "Vaegt_g", "Placering"]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(
                f"Ingen direkte match på {soeg_farve} {soeg_materiale}. Bedste alternativer:"
            )

            samme_mat = aktivt_lager[aktivt_lager["Materiale"] == soeg_materiale]
            if not samme_mat.empty:
                st.write(f"**💡 Samme materiale ({soeg_materiale}), anden farve:**")
                st.dataframe(
                    samme_mat[
                        ["ID", "Farve", "Detalje", "Brand", "Vaegt_g", "Placering"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            samme_farve = aktivt_lager[aktivt_lager["Farve"] == soeg_farve]
            if not samme_farve.empty:
                st.write(f"**🎨 Samme farve ({soeg_farve}), andet materiale:**")
                st.dataframe(
                    samme_farve[
                        ["ID", "Materiale", "Detalje", "Brand", "Vaegt_g", "Placering"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            if samme_mat.empty and samme_farve.empty:
                st.error("Hverken materialet eller farven er på lager lige nu.")

    else:
        resultat = aktivt_lager.copy()
        if soeg_materiale != "Alle":
            resultat = resultat[resultat["Materiale"] == soeg_materiale]
        if soeg_farve != "Alle":
            resultat = resultat[resultat["Farve"] == soeg_farve]

        st.dataframe(
            resultat[
                ["ID", "Materiale", "Farve", "Detalje", "Brand", "Vaegt_g", "Placering"]
            ],
            use_container_width=True,
            hide_index=True,
        )

# --- FANE 2: LAGERBEHOLDNING ---
with tab_lager:
    if df.empty:
        st.info("Lageret er tomt. Tilføj en rulle under '➕ Tilføj'.")
    else:
        st.subheader("Træk forbrug fra efter print")
        rulle_liste = [
            f"ID {row['ID']}: {row['Farve']} {row['Materiale']} ({row['Brand']}) - {row['Vaegt_g']}g"
            for _, row in df.iterrows()
        ]
        valgt_rulle_tekst = st.selectbox(
            "Vælg rulle", rulle_liste, key="forbrug_select"
        )

        brugt_gram = st.number_input(
            "Brugt mængde (gram)", min_value=1, max_value=5000, value=50, step=10
        )

        if st.button("Træk fra ➖", use_container_width=True):
            valgt_id = int(valgt_rulle_tekst.split(":")[0].replace("ID ", ""))
            idx = df.index[df["ID"] == valgt_id][0]
            ny_vaegt = df.at[idx, "Vaegt_g"] - brugt_gram

            if ny_vaegt <= 0:
                df = df[df["ID"] != valgt_id]
                gem_data(df)
                st.toast("Rullen ramte 0g og er slettet! 🗑️")
            else:
                df.at[idx, "Vaegt_g"] = ny_vaegt
                gem_data(df)
                st.toast(f"Opdateret! {ny_vaegt}g tilbage.")
            st.rerun()

        st.divider()

        st.subheader("Samlet lagerbeholdning")
        st.dataframe(
            df[["ID", "Materiale", "Farve", "Detalje", "Brand", "Vaegt_g", "Placering"]],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader("✏️ Rediger eller slet rulle")
        rediger_rulle_tekst = st.selectbox(
            "Vælg rulle", rulle_liste, key="rediger_select"
        )
        rediger_id = int(rediger_rulle_tekst.split(":")[0].replace("ID ", ""))
        rulle_data = df[df["ID"] == rediger_id].iloc[0]

        with st.form("rediger_form"):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                ret_mat = st.selectbox(
                    "Materiale",
                    MATERIALER,
                    index=MATERIALER.index(rulle_data["Materiale"])
                    if rulle_data["Materiale"] in MATERIALER
                    else 0,
                )
                ret_brand = st.selectbox(
                    "Brand",
                    BRANDS,
                    index=BRANDS.index(rulle_data["Brand"])
                    if rulle_data["Brand"] in BRANDS
                    else 0,
                )
                ret_vaegt = st.number_input(
                    "Vægt (g)",
                    min_value=0,
                    max_value=5000,
                    value=int(rulle_data["Vaegt_g"]),
                    step=10,
                )
            with col_r2:
                ret_farve = st.selectbox(
                    "Farve",
                    FARVER,
                    index=FARVER.index(rulle_data["Farve"])
                    if rulle_data["Farve"] in FARVER
                    else 0,
                )
                ret_placering = st.selectbox(
                    "Placering",
                    PLACERINGER,
                    index=PLACERINGER.index(rulle_data["Placering"])
                    if rulle_data["Placering"] in PLACERINGER
                    else 0,
                )
                ret_detalje = st.text_input(
                    "Detalje", value=str(rulle_data["Detalje"])
                )

            gem_rettelse = st.form_submit_button(
                "Gem ændringer 💾", use_container_width=True
            )
            slet_rulle = st.form_submit_button(
                "Slet rulle 🗑️", use_container_width=True
            )

            if gem_rettelse:
                if ret_vaegt <= 0:
                    df = df[df["ID"] != rediger_id]
                    gem_data(df)
                    st.toast("Rullen er slettet! 🗑️")
                else:
                    idx = df.index[df["ID"] == rediger_id][0]
                    df.at[idx, "Materiale"] = ret_mat
                    df.at[idx, "Farve"] = ret_farve
                    df.at[idx, "Detalje"] = ret_detalje
                    df.at[idx, "Brand"] = ret_brand
                    df.at[idx, "Vaegt_g"] = ret_vaegt
                    df.at[idx, "Placering"] = ret_placering
                    gem_data(df)
                    st.toast("Rullen er opdateret! ✅")
                st.rerun()

            if slet_rulle:
                df = df[df["ID"] != rediger_id]
                gem_data(df)
                st.toast("Rullen er slettet! 🗑️")
                st.rerun()

# --- FANE 3: TILFØJ NY RULLE ---
with tab_tilfoej:
    st.subheader("Registrer ny rulle")
    with st.form("ny_rulle_form", clear_on_submit=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            ny_mat = st.selectbox("Materiale", MATERIALER)
            ny_brand = st.selectbox("Brand", BRANDS)
            ny_vaegt = st.number_input(
                "Vægt (gram)", min_value=1, max_value=5000, value=1000, step=50
            )
        with col_t2:
            ny_farve = st.selectbox("Farve", FARVER)
            ny_placering = st.selectbox("Placering", PLACERINGER)
            ny_detalje = st.text_input("Detalje (f.eks. Matte Charcoal)")

        gem_knap = st.form_submit_button("Gem på lageret ✅", use_container_width=True)

        if gem_knap:
            ny_raekke = pd.DataFrame(
                [
                    {
                        "ID": 0,
                        "Materiale": ny_mat,
                        "Farve": ny_farve,
                        "Detalje": ny_detalje,
                        "Brand": ny_brand,
                        "Vaegt_g": ny_vaegt,
                        "Placering": ny_placering,
                    }
                ]
            )
            df = pd.concat([df, ny_raekke], ignore_index=True)
            gem_data(df)
            st.success("Rullen er tilføjet!")
            st.rerun()

# --- FANE 4: FEEDBACK ---
with tab_feedback:
    st.subheader("Send forslag eller fejlmelding")
    with st.form("feedback_form", clear_on_submit=True):
        feedback_type = st.selectbox(
            "Emne",
            [
                "💡 Forslag til ny funktion",
                "🐛 Noget der driller / fejl",
                "➕ Mangler farve/brand",
                "👍 Ros",
            ],
        )
        feedback_besked = st.text_area("Din besked", height=140)
        send_feedback = st.form_submit_button(
            "Send besked 📨", use_container_width=True
        )

        if send_feedback:
            if not feedback_besked.strip():
                st.warning("Skriv venligst en besked først.")
            elif "DIN_KODE_HER" in FORMSPREE_URL:
                st.error("Indsæt dit Formspree-link i koden først.")
            else:
                try:
                    response = requests.post(
                        FORMSPREE_URL,
                        data={
                            "Emne": f"FilaKent Feedback: {feedback_type}",
                            "Besked": feedback_besked,
                        },
                        headers={"Accept": "application/json"},
                    )
                    if response.status_code == 200:
                        st.success("Sendt! Tak for din feedback. 🎉")
                    else:
                        st.error("Kunne ikke sende beskeden lige nu.")
                except Exception:
                    st.error("Forbindelsesfejl.")