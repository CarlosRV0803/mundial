from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================

st.set_page_config(
    page_title="Pronósticos - Semifinales y Final",
    page_icon="🏆",
    layout="wide"
)

ZONA_HORARIA = ZoneInfo("America/Lima")


# ==========================================================
# CONFIGURACIÓN DE PARTIDOS
# Reemplazar por las selecciones reales cuando se conozcan.
# ==========================================================

SEMIFINALES = [
    {
        "partido_id": 1,
        "fase": "Semifinal 1",
        "equipo_a": "Francia",
        "equipo_b": "España",
    },
    {
        "partido_id": 2,
        "fase": "Semifinal 2",
        "equipo_a": "Inglaterra",
        "equipo_b": "Argentina",
    },
]


# ==========================================================
# ESTILOS
# ==========================================================

st.markdown(
    """
    <style>
        .titulo-principal {
            text-align: center;
            font-size: 2.3rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .subtitulo {
            text-align: center;
            color: #666;
            margin-bottom: 2rem;
        }

        .partido-card {
            border: 1px solid #dddddd;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 14px;
            background-color: rgba(128, 128, 128, 0.05);
        }

        .partido-titulo {
            text-align: center;
            font-weight: 700;
            font-size: 1.15rem;
            margin-bottom: 12px;
        }

        .equipo {
            text-align: center;
            font-size: 1.05rem;
            font-weight: 600;
        }

        .clasificado {
            text-align: center;
            font-weight: 700;
            margin-top: 10px;
        }

        div[data-testid="stNumberInput"] input {
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# GOOGLE SHEETS
# ==========================================================

COLUMNAS_RESPUESTAS = [
    "fecha_registro", "nombre", "correo", "partido_id", "fase",
    "partido", "equipo_a", "equipo_b", "goles_a_90", "goles_b_90",
    "clasificado", "eliminado", "momento_clasificacion", "resultado",
]


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
    return spreadsheet.worksheet(st.secrets["GOOGLE_WORKSHEET_NAME"])


def asegurar_encabezados():
    worksheet = conectar_google_sheets()
    valores = worksheet.get_all_values()
    if not valores:
        worksheet.append_row(COLUMNAS_RESPUESTAS)
        return
    if valores[0] != COLUMNAS_RESPUESTAS:
        raise ValueError(
            "Los encabezados de la hoja no coinciden. La fila 1 debe contener: "
            + ", ".join(COLUMNAS_RESPUESTAS)
        )


def leer_respuestas():
    worksheet = conectar_google_sheets()
    asegurar_encabezados()
    registros = worksheet.get_all_records()
    return pd.DataFrame(registros) if registros else pd.DataFrame(columns=COLUMNAS_RESPUESTAS)


def correo_ya_registrado(correo):
    df = leer_respuestas()
    if df.empty or "correo" not in df.columns:
        return False
    correos = df["correo"].astype(str).str.strip().str.lower()
    return correo.strip().lower() in set(correos)


def guardar_respuestas_google_sheets(df_nuevo):
    worksheet = conectar_google_sheets()
    asegurar_encabezados()
    filas = (
        df_nuevo[COLUMNAS_RESPUESTAS]
        .fillna("")
        .astype(str)
        .values
        .tolist()
    )
    worksheet.append_rows(filas, value_input_option="USER_ENTERED")


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def inicializar_estado():
    """Inicializa las variables necesarias en session_state."""

    valores_iniciales = {
        "semifinales_confirmadas": False,
        "ganadores_semis": [],
        "perdedores_semis": [],
        "pronosticos_semis": [],
        "pronostico_tercer_puesto": None,
        "pronostico_final": None,
    }

    for clave, valor in valores_iniciales.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def determinar_clasificado(
    equipo_a,
    equipo_b,
    goles_a,
    goles_b,
    ganador_desempate=None
):
    """
    Determina clasificado, eliminado y momento de clasificación.

    Si el marcador de 90 minutos termina empatado, el usuario debe indicar
    quién clasifica y si lo hace en suplementario o penales.
    """

    if goles_a > goles_b:
        return {
            "clasificado": equipo_a,
            "eliminado": equipo_b,
            "momento_clasificacion": "90 minutos",
        }

    if goles_b > goles_a:
        return {
            "clasificado": equipo_b,
            "eliminado": equipo_a,
            "momento_clasificacion": "90 minutos",
        }

    if ganador_desempate is None:
        return None

    clasificado = ganador_desempate["equipo"]
    eliminado = equipo_b if clasificado == equipo_a else equipo_a

    return {
        "clasificado": clasificado,
        "eliminado": eliminado,
        "momento_clasificacion": ganador_desempate["momento"],
    }


def mostrar_partido(
    identificador,
    fase,
    equipo_a,
    equipo_b,
    permitir_empate_90=True
):
    """
    Muestra los controles para pronosticar un partido eliminatorio.
    Devuelve el pronóstico estructurado.
    """

    st.markdown(
        f"""
        <div class="partido-card">
            <div class="partido-titulo">{fase}</div>
            <div style="display:flex; justify-content:space-around;">
                <div class="equipo">{equipo_a}</div>
                <div class="equipo">{equipo_b}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_a, col_vs, col_b = st.columns([4, 1, 4])

    with col_a:
        st.markdown(
            f"<div class='equipo'>{equipo_a}</div>",
            unsafe_allow_html=True
        )

        goles_a = st.number_input(
            f"Goles de {equipo_a}",
            min_value=0,
            max_value=20,
            value=0,
            step=1,
            key=f"{identificador}_goles_a",
            label_visibility="collapsed"
        )

    with col_vs:
        st.markdown(
            "<div style='text-align:center; padding-top:35px; "
            "font-weight:bold;'>VS</div>",
            unsafe_allow_html=True
        )

    with col_b:
        st.markdown(
            f"<div class='equipo'>{equipo_b}</div>",
            unsafe_allow_html=True
        )

        goles_b = st.number_input(
            f"Goles de {equipo_b}",
            min_value=0,
            max_value=20,
            value=0,
            step=1,
            key=f"{identificador}_goles_b",
            label_visibility="collapsed"
        )

    ganador_desempate = None

    if goles_a == goles_b and permitir_empate_90:
        st.info(
            "El marcador termina empatado en los 90 minutos. "
            "Indica quién clasifica y en qué momento."
        )

        col_clasificado, col_momento = st.columns(2)

        with col_clasificado:
            equipo_clasificado = st.selectbox(
                "Equipo clasificado",
                options=["Seleccionar", equipo_a, equipo_b],
                key=f"{identificador}_clasificado"
            )

        with col_momento:
            momento = st.selectbox(
                "Momento de clasificación",
                options=["Seleccionar", "Suplementario", "Penales"],
                key=f"{identificador}_momento"
            )

        if (
            equipo_clasificado != "Seleccionar"
            and momento != "Seleccionar"
        ):
            ganador_desempate = {
                "equipo": equipo_clasificado,
                "momento": momento,
            }

    resultado = determinar_clasificado(
        equipo_a=equipo_a,
        equipo_b=equipo_b,
        goles_a=goles_a,
        goles_b=goles_b,
        ganador_desempate=ganador_desempate
    )

    if resultado is None:
        st.warning("Falta indicar quién clasifica.")
        return None

    st.success(
        f"Clasifica: **{resultado['clasificado']}** "
        f"({resultado['momento_clasificacion']})"
    )

    return {
        "fase": fase,
        "equipo_a": equipo_a,
        "equipo_b": equipo_b,
        "goles_a_90": int(goles_a),
        "goles_b_90": int(goles_b),
        "clasificado": resultado["clasificado"],
        "eliminado": resultado["eliminado"],
        "momento_clasificacion": resultado["momento_clasificacion"],
        "resultado": (
            f"{resultado['clasificado']} | "
            f"{resultado['momento_clasificacion']} | "
            f"{int(goles_a)} - {int(goles_b)}"
        ),
    }


def construir_registros(nombre, correo):
    """Convierte los pronósticos de la llave en registros de detalle."""

    fecha_registro = datetime.now(ZONA_HORARIA).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    partidos = (
        st.session_state.pronosticos_semis
        + [
            st.session_state.pronostico_tercer_puesto,
            st.session_state.pronostico_final,
        ]
    )

    registros = []

    for numero, partido in enumerate(partidos, start=1):
        registro = {
            "fecha_registro": fecha_registro,
            "nombre": nombre.strip(),
            "correo": correo.strip().lower(),
            "partido_id": numero,
            "fase": partido["fase"],
            "partido": f"{partido['equipo_a']} vs {partido['equipo_b']}",
            "equipo_a": partido["equipo_a"],
            "equipo_b": partido["equipo_b"],
            "goles_a_90": partido["goles_a_90"],
            "goles_b_90": partido["goles_b_90"],
            "clasificado": partido["clasificado"],
            "eliminado": partido["eliminado"],
            "momento_clasificacion": partido["momento_clasificacion"],
            "resultado": partido["resultado"],
        }

        registros.append(registro)

    return pd.DataFrame(registros)


def reiniciar_llave():
    """Limpia los pronósticos manteniendo nombre y correo."""

    claves_a_borrar = [
        clave
        for clave in st.session_state.keys()
        if (
            clave.startswith("semi_")
            or clave.startswith("final_")
            or clave.startswith("tercer_")
        )
    ]

    for clave in claves_a_borrar:
        del st.session_state[clave]

    st.session_state.semifinales_confirmadas = False
    st.session_state.ganadores_semis = []
    st.session_state.perdedores_semis = []
    st.session_state.pronosticos_semis = []
    st.session_state.pronostico_tercer_puesto = None
    st.session_state.pronostico_final = None


# ==========================================================
# INICIO DE LA APLICACIÓN
# ==========================================================

inicializar_estado()

st.markdown(
    "<div class='titulo-principal'>🏆 Pronósticos del Mundial</div>",
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class='subtitulo'>
        Completa las semifinales para construir automáticamente tu final
        y el partido por el tercer puesto.
    </div>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# DATOS DEL PARTICIPANTE
# ==========================================================

st.subheader("👤 Datos del participante")

col_nombre, col_correo = st.columns(2)

with col_nombre:
    nombre = st.text_input(
        "Nombre completo",
        key="nombre_participante"
    )

with col_correo:
    correo = st.text_input(
        "Correo electrónico",
        key="correo_participante"
    )

st.divider()


# ==========================================================
# SEMIFINALES
# ==========================================================

st.header("1. Semifinales")

if not st.session_state.semifinales_confirmadas:

    pronosticos_semis_temporales = []

    columnas_semis = st.columns(2)

    for indice, partido in enumerate(SEMIFINALES):
        with columnas_semis[indice]:
            pronostico = mostrar_partido(
                identificador=f"semi_{partido['partido_id']}",
                fase=partido["fase"],
                equipo_a=partido["equipo_a"],
                equipo_b=partido["equipo_b"],
            )

            pronosticos_semis_temporales.append(pronostico)

    st.write("")

    puede_confirmar = all(
        pronostico is not None
        for pronostico in pronosticos_semis_temporales
    )

    if st.button(
        "Confirmar semifinales y completar la llave",
        type="primary",
        use_container_width=True,
        disabled=not puede_confirmar
    ):
        st.session_state.pronosticos_semis = (
            pronosticos_semis_temporales
        )

        st.session_state.ganadores_semis = [
            pronostico["clasificado"]
            for pronostico in pronosticos_semis_temporales
        ]

        st.session_state.perdedores_semis = [
            pronostico["eliminado"]
            for pronostico in pronosticos_semis_temporales
        ]

        st.session_state.semifinales_confirmadas = True
        st.rerun()

else:
    st.success("Semifinales confirmadas. La llave fue completada.")

    resumen_semis = pd.DataFrame(
        [
            {
                "Partido": partido["fase"],
                "Resultado a 90 minutos": (
                    f"{partido['equipo_a']} "
                    f"{partido['goles_a_90']} - "
                    f"{partido['goles_b_90']} "
                    f"{partido['equipo_b']}"
                ),
                "Clasificado": partido["clasificado"],
                "Momento": partido["momento_clasificacion"],
            }
            for partido in st.session_state.pronosticos_semis
        ]
    )

    st.dataframe(
        resumen_semis,
        hide_index=True,
        use_container_width=True
    )

    if st.button(
        "Modificar semifinales",
        use_container_width=True
    ):
        reiniciar_llave()
        st.rerun()


# ==========================================================
# FINAL Y TERCER PUESTO
# ==========================================================

if st.session_state.semifinales_confirmadas:

    st.divider()
    st.header("2. Llave definida según tus pronósticos")

    finalista_1, finalista_2 = st.session_state.ganadores_semis
    tercero_1, tercero_2 = st.session_state.perdedores_semis

    col_tercer_puesto, col_final = st.columns(2)

    with col_tercer_puesto:
        st.subheader("🥉 Tercer y cuarto puesto")

        pronostico_tercer_puesto = mostrar_partido(
            identificador="tercer_puesto",
            fase="Tercer y cuarto puesto",
            equipo_a=tercero_1,
            equipo_b=tercero_2,
        )

    with col_final:
        st.subheader("🏆 Final")

        pronostico_final = mostrar_partido(
            identificador="final_mundial",
            fase="Final",
            equipo_a=finalista_1,
            equipo_b=finalista_2,
        )

    st.session_state.pronostico_tercer_puesto = (
        pronostico_tercer_puesto
    )

    st.session_state.pronostico_final = pronostico_final


# ==========================================================
# RESUMEN Y ENVÍO
# ==========================================================

if (
    st.session_state.semifinales_confirmadas
    and st.session_state.pronostico_tercer_puesto is not None
    and st.session_state.pronostico_final is not None
):

    st.divider()
    st.header("3. Resumen de tu llave")

    campeon = st.session_state.pronostico_final["clasificado"]
    subcampeon = st.session_state.pronostico_final["eliminado"]
    tercer_puesto = (
        st.session_state.pronostico_tercer_puesto["clasificado"]
    )
    cuarto_puesto = (
        st.session_state.pronostico_tercer_puesto["eliminado"]
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🏆 Campeón", campeon)
    col2.metric("🥈 Subcampeón", subcampeon)
    col3.metric("🥉 Tercer puesto", tercer_puesto)
    col4.metric("4.º puesto", cuarto_puesto)

    partidos_resumen = (
        st.session_state.pronosticos_semis
        + [
            st.session_state.pronostico_tercer_puesto,
            st.session_state.pronostico_final,
        ]
    )

    df_resumen = pd.DataFrame(
        [
            {
                "Fase": partido["fase"],
                "Partido": (
                    f"{partido['equipo_a']} vs "
                    f"{partido['equipo_b']}"
                ),
                "Marcador 90 minutos": (
                    f"{partido['goles_a_90']} - "
                    f"{partido['goles_b_90']}"
                ),
                "Clasificado": partido["clasificado"],
                "Momento": partido["momento_clasificacion"],
            }
            for partido in partidos_resumen
        ]
    )

    st.dataframe(
        df_resumen,
        hide_index=True,
        use_container_width=True
    )

    correo_valido = (
        "@" in correo
        and "." in correo.split("@")[-1]
    )

    datos_validos = (
        bool(nombre.strip())
        and correo_valido
    )

    if not datos_validos:
        st.warning(
            "Completa correctamente tu nombre y correo antes de enviar."
        )

    confirmacion = st.checkbox(
        "Confirmo que revisé todos mis pronósticos."
    )

    if st.button(
        "Enviar pronósticos",
        type="primary",
        use_container_width=True,
        disabled=not datos_validos or not confirmacion
    ):
        try:
            df_registros = construir_registros(
                nombre=nombre,
                correo=correo
            )

            if correo_ya_registrado(correo):
                st.error(
                    "Este correo ya registró una respuesta. "
                    "Si necesitas modificarla, comunícate con el organizador."
                )
            else:
                guardar_respuestas_google_sheets(df_registros)
                st.success(
                    "✅ Tus pronósticos fueron registrados correctamente en Google Sheets."
                )
                st.balloons()


        except Exception as error:
            st.error(
                "No se pudieron guardar los pronósticos. "
                f"Detalle: {error}"
            )
