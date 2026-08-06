import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import base64
from datetime import datetime
import json

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Pixel Thread 🧵",
    page_icon="🧵",
    layout="wide"
)

# ---------------------------------------------------------
# 2. CONEXIÓN A FIREBASE (FIRESTORE)
# ---------------------------------------------------------
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # Cargamos los secretos usando la clave FIREBASE_CREDENTIALS
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------------------------------------------------
# 3. FUNCIONES DE BASE DE DATOS
# ---------------------------------------------------------
def guardar_logo_firebase(nuevo_logo):
    db.collection("logos").document(str(nuevo_logo["id"])).set(nuevo_logo)

def obtener_logos_cliente(nombre_cliente):
    docs = db.collection("logos").where("cliente", "==", nombre_cliente).stream()
    return [doc.to_dict() for doc in docs]

# ---------------------------------------------------------
# 4. BARRA LATERAL (INICIO DE SESIÓN PERSISTENTE)
# ---------------------------------------------------------
st.sidebar.title("Pixel Thread 🧵")
st.sidebar.subheader("🔒 Iniciar Sesión")

# Inicializamos el estado si no existe
if "usuario_activo" not in st.session_state:
    st.session_state["usuario_activo"] = "Cliente A"
if "tipo_acceso" not in st.session_state:
    st.session_state["tipo_acceso"] = "Cliente"

# Inputs de la barra lateral
tipo_acceso = st.sidebar.radio(
    "Tipo de Acceso", 
    ["Cliente", "Panel Administrador"], 
    key="input_tipo"
)
nombre_usuario = st.sidebar.text_input(
    "Ingresa tu Nombre de Usuario", 
    value=st.session_state["usuario_activo"]
)

# Botón para actualizar el usuario
if st.sidebar.button("Entrar a mi Portal"):
    st.session_state["usuario_activo"] = nombre_usuario
    st.session_state["tipo_acceso"] = tipo_acceso
    st.rerun()

# Recuperamos el valor para usarlo en la app
usuario_activo = st.session_state["usuario_activo"]

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tarifa oficial:** 5.00 USD / 300.00 DOP por logo.")

# ---------------------------------------------------------
# 5. CONTENIDO PRINCIPAL
# ---------------------------------------------------------
st.title(f"Portal de Cliente: {usuario_activo}")

divisa = st.radio("Selecciona tu moneda:", ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"], horizontal=True)
st.markdown("---")

# ---------------------------------------------------------
# 6. FORMULARIO: ENVIAR NUEVO LOGO
# ---------------------------------------------------------
with st.expander("➕ Enviar Nuevo Logo", expanded=True):
    nombre_logo = st.text_input("1. Nombre del Logo / Proyecto")
    archivos_subidos = st.file_uploader("2. Sube tu archivo", type=["png", "jpg", "pdf", "dst", "emb"], accept_multiple_files=False)
    tipo_aplicacion = st.radio("3. Soporte del bordado:", ["Tela (Camisetas, Polos, etc.)", "Gorra"])

    ubicacion_gorra, detalle_gorra = "N/A", "N/A"
    if tipo_aplicacion == "Gorra":
        col1, col2 = st.columns(2)
        ubicacion_gorra = col1.selectbox("Ubicación:", ["Frente", "Lado Izquierdo", "Lado Derecho", "Atrás"])
        detalle_gorra = col2.selectbox("Estructura:", ["Plana / Estructurada", "Curva / Soft", "3D / Relevante"])

    comentario_cliente = st.text_area("4. Instrucciones especiales")

    if st.button("🚀 ENVIAR LOGO A PIXEL THREAD"):
        if nombre_logo:
            img_bytes_guardar = None
            if archivos_subidos:
                img_bytes_guardar = base64.b64encode(archivos_subidos.getvalue()).decode("utf-8")

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
                "comentario": comentario_cliente,
                "archivo": archivos_subidos.name if archivos_subidos else "Sin archivo",
                "imagen_bytes": img_bytes_guardar
            }
            guardar_logo_firebase(nuevo_logo)
            st.success("¡Logo enviado exitosamente a Firebase!")
            st.rerun()

# ---------------------------------------------------------
# 7. HISTORIAL
# ---------------------------------------------------------
st.header("📋 Mis Pedidos Registrados")
try:
    pedidos = obtener_logos_cliente(usuario_activo)
    if pedidos:
        for p in pedidos:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.subheader(p.get("nombre", "Sin Nombre"))
                precio = p.get("precio_usd", 5.0) if "USD" in divisa else p.get("precio_dop", 300.0)
                moneda = "USD" if "USD" in divisa else "DOP"
                c2.markdown(f"**Precio:** {precio:.2f} {moneda}")
                c3.markdown(f"**Estado:** {p.get('estado', 'Pendiente')}")
                c4.markdown(f"**Pago:** {p.get('pago', 'Pendiente')}")
                st.divider()
    else:
        st.info("No tienes solicitudes guardadas en el sistema.")
except Exception as e:
    st.error(f"Error al conectar con Firestore: {e}")