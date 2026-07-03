import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# =====================================================
# Configuración general
# =====================================================

st.set_page_config(
    page_title="Polla Mundialista - 8vos",
    page_icon="⚽",
    layout="centered"
)

# En Streamlit Cloud NO uses rutas de Windows.
# Este archivo se creará en el entorno donde corra la app.
ARCHIVO_RESPUESTAS = Path(r"respuestas_8vos.csv")

# =====================================================
# Partidos
# Cambia esta lista por los cruces reales
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
# Funciones
# =====================================================

def obtener_opciones_validas(equipo_a, equipo_b, goles_a, goles_b):
    """
    Devuelve:
    - opciones válidas de clasificado
    - opciones válidas de momento
    - mensaje explicativo
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


def guardar_respuestas(df_nuevo, archivo):
    if archivo.exists():
        df_anterior = pd.read_csv(archivo)
        df_final = pd.concat([df_anterior, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo

    df_final.to_csv(archivo, index=False, encoding="utf-8-sig")


def correo_ya_registrado(correo, archivo):
    if not archivo.exists():
        return False

    df = pd.read_csv(archivo)

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


def validar_email_basico(correo):
    correo = correo.strip()

    if "@" not in correo:
        return False

    if "." not in correo:
        return False

    return True


def limpiar_estado_partidos():
    """
    Limpia los widgets de pronóstico luego de un registro exitoso.
    """
    for partido in PARTIDOS:
        partido_id = partido["id"]

        keys = [
            f"goles_a_{partido_id}",
            f"goles_b_{partido_id}",
            f"clasificado_{partido_id}",
            f"momento_{partido_id}",
        ]

        for key in keys:
            if key in st.session_state:
                del st.session_state[key]


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

    elif correo_ya_registrado(correo_limpio, ARCHIVO_RESPUESTAS):
        st.error(
            "Este correo ya registró una respuesta. "
            "Si necesitas modificarla, comunícate con el organizador."
        )

    else:
        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        filas = []

        for respuesta in respuestas:
            filas.append({
                "fecha_registro": fecha_registro,
                "nombre": nombre_limpio,
                "correo": correo_limpio,
                **respuesta
            })

        df_nuevo = pd.DataFrame(filas)

        guardar_respuestas(df_nuevo, ARCHIVO_RESPUESTAS)

        st.success("Tus pronósticos fueron registrados correctamente.")

        st.write("Resumen de tu registro:")
        st.dataframe(df_nuevo, use_container_width=True)
