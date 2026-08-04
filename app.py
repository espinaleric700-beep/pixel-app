import base64
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Pixel Thread 🧵",
    page_icon="🧵",
    layout="wide"
)

# ---------------------------------------------------------
# 2. CONEXIÓN A SUPABASE
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Error conectando con Supabase: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. FUNCIONES DE BASE DE DATOS
# ---------------------------------------------------------
def guardar_logo_supabase(nuevo_logo):
    response = supabase.table("logos").upsert(nuevo_logo).execute()
    return response

def obtener_logos_cliente(nombre_cliente):
    response = (
        supabase.table("logos")
        .select("*")
        .eq("cliente", nombre_cliente)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data

# ---------------------------------------------------------
# 4. BARRA LATERAL (INICIO DE SESIÓN)
# ---------------------------------------------------------
st.sidebar.title("Pixel Thread 🧵")
st.sidebar.subheader("🔒 Iniciar Sesión")

tipo_acceso = st.sidebar.radio("Tipo de Acceso", ["Cliente", "Panel Administrador"])
nombre_usuario = st.sidebar.text_input("Ingresa tu Nombre de Usuario", value="Cliente A")

if st.sidebar.button("Entrar a mi Portal"):
    st.session_state["usuario_activo"] = nombre_usuario
    st.session_state["tipo_acceso"] = tipo_acceso

usuario_activo = st.session_state.get("usuario_activo", "Cliente A")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tarifa oficial:** 5.00 USD / 300.00 DOP por logo digitalizado.")

# ---------------------------------------------------------
# 5. CONTENIDO PRINCIPAL (PORTAL DEL CLIENTE)
# ---------------------------------------------------------
st.title(f"Portal de Cliente: {usuario_activo}")

divisa = st.radio(
    "Selecciona tu moneda:",
    ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"],
    horizontal=True
)

st.markdown("---")

# ---------------------------------------------------------
# 6. FORMULARIO: ENVIAR NUEVO LOGO
# ---------------------------------------------------------
with st.expander("➕ Enviar Nuevo Logo", expanded=True):
    nombre_logo = st.text_input("1. Nombre del Logo / Proyecto")
    
    archivos_subidos = st.file_uploader(
        "2. Sube tu archivo original",
        type=["png", "jpg", "jpeg", "pdf", "dst", "emb", "zip"],
        accept_multiple_files=True
    )

    tipo_aplicacion = st.radio(
        "3. Soporte del bordado:",
        ["Tela (Camisetas, Polos, etc.)", "Gorra"]
    )

    ubicacion_gorra = "N/A"
    detalle_gorra = "N/A"

    if tipo_aplicacion == "Gorra":
        col1, col2 = st.columns(2)
        with col1:
            ubicacion_gorra = st.selectbox(
                "Ubicación en la gorra:",
                ["Frente", "Lado Izquierdo", "Lado Derecho", "Atrás"]
            )
        with col2:
            detalle_gorra = st.selectbox(
                "Estructura de la gorra:",
                ["Plana / Estructurada", "Curva / Soft", "3D / Relevante"]
            )

    comentario_cliente = st.text_area("4. Instrucciones especiales")

    # BOTÓN DE ENVÍO Y GUARDADO EN SUPABASE
    if st.button("🚀 ENVIAR LOGO A PIXEL THREAD"):
        if nombre_logo:
            img_bytes_guardar = None
            if archivos_subidos:
                # Convertir los bytes del archivo cargado a cadena base64 para guardarlo en la base de datos
                bytes_data = archivos_subidos[0].getvalue()
                img_bytes_guardar = base64.b64encode(bytes_data).decode("utf-8")

            nuevo_logo = {
                "id": int(datetime.now().timestamp()),
                "cliente": usuario_activo,
                "nombre": nombre_logo,
                "precio_usd": 5.0,
                "precio_dop": 300.0,
                "estado": "Pendiente",
                "pago": "Pendiente",
                "tipo": tipo_aplicacion,
                "ubicacion_gorra": ubicacion_gorra,
                "detalle_gorra": detalle_gorra,
                "comentario": comentario_cliente if comentario_cliente else "Ninguno",
                "archivo": archivos_subidos[0].name if archivos_subidos else "Sin archivo",
                "imagen_bytes": img_bytes_guardar
            }

            try:
                guardar_logo_supabase(nuevo_logo)
                st.success("¡Logo enviado e ingresado a la base de datos exitosamente!")
                st.rerun()
            except Exception as err:
                st.error(f"Error procesando la solicitud: {err}")
        else:
            st.error("Ingresa un nombre para el logo.")

st.markdown("---")

# ---------------------------------------------------------
# 7. HISTORIAL DE PEDIDOS REGISTRADOS
# ---------------------------------------------------------
st.header("📋 Mis Pedidos Registrados")

try:
    pedidos = obtener_logos_cliente(usuario_activo)
    if pedidos:
        for p in pedidos:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                with c1:
                    st.subheader(p.get("nombre", "Sin Nombre"))
                    st.caption(f"Tipo: {p.get('tipo', 'N/A')} | Archivo: {p.get('archivo', 'N/A')}")
                with c2:
                    precio = p.get("precio_usd", 5.0) if "USD" in divisa else p.get("precio_dop", 300.0)
                    moneda = "USD" if "USD" in divisa else "DOP"
                    st.markdown(f"**Precio:** {precio:.2f} {moneda}")
                with c3:
                    st.markdown(f"**Estado:** {p.get('estado', 'Pendiente')}")
                with c4:
                    st.markdown(f"**Pago:** {p.get('pago', 'Pendiente')}")
                st.divider()
    else:
        st.info("No tienes solicitudes guardadas en el sistema.")
except Exception as e:
    st.error(f"Error al obtener historial: {e}")
