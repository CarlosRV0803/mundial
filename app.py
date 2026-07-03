import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# Configuración general
# =====================================================

st.set_page_config(
    page_title="Polla Mundialista - 8vos",
    page_icon="⚽",
    layout="centered"
)

# =====================================================
# Columnas esperadas en Google Sheets
# =====================================================

COLUMNAS_RESPUESTAS = [
    "fecha_registro",
    "nombre",
    "correo",
    "partido_id",
    "partido",
    "equipo_a",
    "equipo_b",
    "goles_a_90",
    "goles_b_90",
    "clasificado",
    "momento_clasificacion",
]

# =====================================================
# Partidos
# =====================================================

PARTIDOS = [
    {"id": 1, "equipo_a": "Canadá", "equipo_b": "Marruecos"},
    {"id": 2, "equipo_a": "Paraguay", "equipo_b": "Francia"},
    {"id": 3, "equipo_a": "Brasil", "equipo_b": "Noruega"},
    {"id": 4, "equipo_a": "México", "equipo_b": "Inglaterra"},
    {"id": 5, "equipo_a": "Portugal", "equipo_b": "España"},
    {"id": 6, "equipo_a": "Estados Unidos", "equipo_b": "Bélgica"},
    {"id": 7, "equipo_a": "A", "equipo_b": "B"},
    {"id": 8, "equipo_a": "Suiza", "equipo_b": "C"},
]

# =====================================================
# Conexión a Google Sheets
# =====================================================

@st.cache_resource
def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    worksheet = spreadsheet.worksheet(st.secrets["GOOGLE_WORKSHEET_NAME"])

    return worksheet


def asegurar_encabezados():
    """
    Verifica si la hoja tiene encabezados.
    Si está vacía, agrega los encabezados esperados.
    """

    worksheet = conectar_google_sheets()
    valores = worksheet.get_all_values()

    if not valores:
        worksheet.append_row(COLUMNAS_RESPUESTAS)
        return

    encabezados_actuales = valores[0]

    if encabezados_actuales != COLUMNAS_RESPUESTAS:
        st.warning(
            "Los encabezados de Google Sheets no coinciden exactamente con los esperados. "
            "Revisa la primera fila de la hoja."
        )


def leer_respuestas():
    """
    Lee todas las respuestas desde Google Sheets.
    """

    worksheet = conectar_google_sheets()
    asegurar_encabezados()

    registros = worksheet.get_all_records()

    if not registros:
        return pd.DataFrame(columns=COLUMNAS_RESPUESTAS)

    df = pd.DataFrame(registros)

    return df


def guardar_respuestas_google_sheets(df_nuevo):
    """
    Agrega nuevas respuestas a Google Sheets.
    """

    worksheet = conectar_google_sheets()
    asegurar_encabezados()

    df_nuevo = df_nuevo[COLUMNAS_RESPUESTAS].copy()

    filas = df_nuevo.astype(str).values.tolist()

    worksheet.append_rows(
        filas,
        value_input_option="USER_ENTERED"
    )


def correo_ya_registrado(correo):
    """
    Valida si el correo ya fue registrado anteriormente.
    """

    df = leer_respuestas()

    if df.empty:
        return False

    if "correo" not in df.columns:
        return False

    correos_registrados = (
        df["correo"]
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
    )

    return correo.strip().lower() in correos_registrados


# =====================================================
# Funciones de validación
# =====================================================

def obtener_opciones_validas(equipo_a, equipo_b, goles_a, goles_b):
    """
    Reglas:
    - Si equipo_a gana a los 90', clasifica equipo_a y momento = 90 minutos.
    - Si equipo_b gana a los 90', clasifica equipo_b y momento = 90 minutos.
    - Si hay empate a los 90', puede clasificar cualquiera, pero solo en suplementario o penales.
    """

    if goles_a > goles_b:
        return (
            [equipo_a],
            ["90 minutos"],
            f"{equipo_a} gana a los 90 minutos. Clasifica automáticamente {equipo_a}."
        )

    elif goles_b > goles_a:
        return (
            [equipo_b],
            ["90 minutos"],
            f"{equipo_b} gana a los 90 minutos. Clasifica automáticamente {equipo_b}."
        )

    else:
        return (
            [equipo_a, equipo_b],
            ["Suplementario", "Penales"],
            "Empate a los 90 minutos. El partido debe definirse en suplementario o penales."
        )


def validar_email_basico(correo):
    """
    Validación básica de correo.
    """

    correo = correo.strip()

    if "@" not in correo:
        return False

    if "." not in correo:
        return False

    return True


# =====================================================
# Interfaz
# =====================================================

st.title("⚽ Polla Mundialista - 8vos de final")

st.write(
    "Registra tus pronósticos para cada partido: resultado a los 90 minutos, "
    "equipo clasificado y momento de clasificación."
)

st.info(
    "Si un equipo gana a los 90 minutos, la app solo permitirá seleccionar a ese equipo "
    "y el momento será 90 minutos. Si hay empate, la clasificación deberá definirse "
    "en suplementario o penales."
)

st.subheader("Datos del participante")

nombre = st.text_input("Nombre completo", key="nombre")
correo = st.text_input("Correo electrónico", key="correo")

st.divider()
st.subheader("Pronósticos")

respuestas = []

for partido in PARTIDOS:

    partido_id = partido["id"]
    equipo_a = partido["equipo_a"]
    equipo_b = partido["equipo_b"]

    st.markdown(f"### {partido_id}. {equipo_a} vs {equipo_b}")

    col1, col2 = st.columns(2)

    with col1:
        goles_a = st.number_input(
            f"Goles de {equipo_a} a los 90'",
            min_value=0,
            max_value=20,
            step=1,
            value=0,
            key=f"goles_a_{partido_id}"
        )

    with col2:
        goles_b = st.number_input(
            f"Goles de {equipo_b} a los 90'",
            min_value=0,
            max_value=20,
            step=1,
            value=0,
            key=f"goles_b_{partido_id}"
        )

    opciones_clasificado, opciones_momento, mensaje_resultado = obtener_opciones_validas(
        equipo_a,
        equipo_b,
        goles_a,
        goles_b
    )

    st.caption(mensaje_resultado)

    key_clasificado = f"clasificado_{partido_id}"
    key_momento = f"momento_{partido_id}"

    # Forzar consistencia en session_state
    if key_clasificado not in st.session_state:
        st.session_state[key_clasificado] = opciones_clasificado[0]

    if st.session_state[key_clasificado] not in opciones_clasificado:
        st.session_state[key_clasificado] = opciones_clasificado[0]

    if key_momento not in st.session_state:
        st.session_state[key_momento] = opciones_momento[0]

    if st.session_state[key_momento] not in opciones_momento:
        st.session_state[key_momento] = opciones_momento[0]

    clasificado = st.radio(
        "¿Quién clasifica?",
        options=opciones_clasificado,
        horizontal=True,
        key=key_clasificado,
        disabled=len(opciones_clasificado) == 1
    )

    momento = st.selectbox(
        "¿En qué momento clasifica?",
        options=opciones_momento,
        key=key_momento,
        disabled=len(opciones_momento) == 1
    )

    respuestas.append({
        "partido_id": partido_id,
        "partido": f"{equipo_a} vs {equipo_b}",
        "equipo_a": equipo_a,
        "equipo_b": equipo_b,
        "goles_a_90": goles_a,
        "goles_b_90": goles_b,
        "clasificado": clasificado,
        "momento_clasificacion": momento
    })

    st.divider()


# =====================================================
# Botón de envío
# =====================================================

enviar = st.button("Enviar pronósticos", type="primary")

if enviar:

    nombre_limpio = nombre.strip()
    correo_limpio = correo.strip().lower()

    if not nombre_limpio:
        st.error("Debes ingresar tu nombre completo.")

    elif not correo_limpio:
        st.error("Debes ingresar tu correo electrónico.")

    elif not validar_email_basico(correo_limpio):
        st.error("Debes ingresar un correo válido.")

    elif correo_ya_registrado(correo_limpio):
        st.error(
            "Este correo ya registró una respuesta. "
            "Si necesitas modificarla, comunícate con el organizador."
        )

    else:
        fecha_registro = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")

        filas = []

        for respuesta in respuestas:
            filas.append({
                "fecha_registro": fecha_registro,
                "nombre": nombre_limpio,
                "correo": correo_limpio,
                **respuesta
            })

        df_nuevo = pd.DataFrame(filas)

        guardar_respuestas_google_sheets(df_nuevo)

        st.success("Tus pronósticos fueron registrados correctamente.")
        st.info("Las respuestas fueron guardadas en Google Sheets.")

        st.write("Resumen de tu registro:")
        st.dataframe(df_nuevo, use_container_width=True)
