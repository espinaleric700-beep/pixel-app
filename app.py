import streamlit as st
from PIL import Image
from datetime import datetime
import os
import io
import base64
from supabase import create_client, Client

# --- LIBRERÍAS DE GOOGLE DRIVE ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Pixel Thread - Portal Profesional", layout="centered")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error conectando con Supabase: {e}")
        return None

supabase: Client = init_supabase()

# --- SUBIDA A GOOGLE DRIVE ---
def subir_a_google_drive(file_bytes, nombre_archivo, mime_type="image/png"):
    try:
        creds_dict = st.secrets["gserviceaccount"]
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)

        folder_id = st.secrets.get("gdrive_folder_id", None)
        file_metadata = {'name': nombre_archivo}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        return file.get('webViewLink')
    except Exception as e:
        st.warning(f"No se pudo guardar en Drive: {e}")
        return None

# --- CARGAR DESDE SUPABASE EN CADA RECARGA ---
def cargar_datos_supabase():
    if not supabase:
        return []
    try:
        res_logos = supabase.table("logos").select("*").execute()
        logos_list = []
        if res_logos.data:
            for row in res_logos.data:
                img_bytes = None
                if row.get("imagen_bytes"):
                    try:
                        img_bytes = base64.b64decode(row["imagen_bytes"].encode("utf-8"))
                    except:
                        img_bytes = None

                logos_list.append({
                    "id": row.get("id"),
                    "cliente": row.get("cliente"),
                    "nombre": row.get("nombre"),
                    "precio_usd": row.get("precio_usd", 5.0),
                    "precio_dop": row.get("precio_dop", 300.0),
                    "estado": row.get("estado", "Pendiente"),
                    "pago": row.get("pago", "Pendiente"),
                    "tipo": row.get("tipo", "Tela"),
                    "ubicacion_gorra": row.get("ubicacion_gorra", "N/A"),
                    "detalle_gorra": row.get("detalle_gorra", "N/A"),
                    "comentario": row.get("comentario", "Ninguno"),
                    "archivo": row.get("archivo", "Sin archivo"),
                    "imagen_bytes": img_bytes,
                    "gdrive_url": row.get("gdrive_url")
                })
        return logos_list
    except Exception as e:
        st.error(f"Error al leer Supabase: {e}")
        return []

def guardar_logo_supabase(logo_dict):
    if not supabase:
        return
    logo_db = {
        "id": logo_dict["id"],
        "cliente": logo_dict.get("cliente"),
        "nombre": logo_dict.get("nombre"),
        "precio_usd": logo_dict.get("precio_usd", 5.0),
        "precio_dop": logo_dict.get("precio_dop", 300.0),
        "estado": logo_dict.get("estado", "Pendiente"),
        "pago": logo_dict.get("pago", "Pendiente"),
        "tipo": logo_dict.get("tipo", "Tela"),
        "ubicacion_gorra": logo_dict.get("ubicacion_gorra", "N/A"),
        "detalle_gorra": logo_dict.get("detalle_gorra", "N/A"),
        "comentario": logo_dict.get("comentario", "Ninguno"),
        "archivo": logo_dict.get("archivo", "Sin archivo"),
        "gdrive_url": logo_dict.get("gdrive_url"),
        "imagen_bytes": base64.b64encode(logo_dict["imagen_bytes"]).decode("utf-8") if logo_dict.get("imagen_bytes") else None
    }
    supabase.table("logos").upsert(logo_db).execute()

# --- FORZAR CARGA DE DATOS EN CADA EJECUCIÓN/RECARGA ---
st.session_state.logos = cargar_datos_supabase()

if "sesion_activa" not in st.session_state:
    st.session_state.sesion_activa = None

# --- MENÚ LATERAL ---
st.sidebar.title("Pixel Thread 🧵")
if st.session_state.sesion_activa is None:
    st.sidebar.subheader("🔒 Iniciar Sesión")
    tipo = st.sidebar.radio("Tipo de Acceso", ["Cliente", "Panel Administrador"])
    if tipo == "Panel Administrador":
        pin = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Entrar Admin"):
            if pin == "2580PIXEL":
                st.session_state.sesion_activa = "admin"
                st.rerun()
            else:
                st.error("PIN incorrecto")
    else:
        user = st.sidebar.text_input("Nombre de Usuario / Cliente")
        if st.sidebar.button("Entrar"):
            if user.strip():
                st.session_state.sesion_activa = user.strip()
                st.rerun()
            else:
                st.warning("Escribe un nombre de usuario.")
    st.stop()
else:
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.sesion_activa = None
        st.rerun()

# --- VISTA CLIENTE ---
nombre_cliente = st.session_state.sesion_activa
st.title(f"Portal de Cliente: {nombre_cliente}")

st.markdown("### 📤 Cargar Nuevo Diseño")

nombre_logo = st.text_input("1. Nombre del Logo / Diseño *")
archivo_subido = st.file_uploader("2. Sube tu archivo original", type=["png", "jpg", "jpeg", "pdf", "ai"])
tipo_aplicacion = st.radio("3. Soporte del bordado:", ["Tela (Camisetas, Polos, etc.)", "Gorra"])

ubicacion_gorra = "N/A"
detalle_gorra = "N/A"
if tipo_aplicacion == "Gorra":
    ubicacion_gorra = st.radio("Ubicación:", ["Frontal", "Trasero", "Lateral"])
    detalle_gorra = st.radio("Estilo:", ["3D (Puff)", "Plano (Flat)"]) if ubicacion_gorra == "Frontal" else "Plano (Flat)"

comentario_cliente = st.text_area("4. Instrucciones especiales")

if st.button("🚀 ENVIAR LOGO A PIXEL THREAD", use_container_width=True):
    if not nombre_logo.strip():
        st.error("❌ Escribe un nombre para el logo.")
    else:
        with st.spinner("⏳ Guardando en base de datos..."):
            try:
                img_bytes = None
                nombre_archivo = "Sin archivo"
                url_drive = None

                if archivo_subido is not None:
                    img_bytes = archivo_subido.getvalue()
                    nombre_archivo = archivo_subido.name
                    mime = archivo_subido.type or "application/octet-stream"
                    url_drive = subir_a_google_drive(img_bytes, f"{nombre_cliente}_{nombre_logo}_{nombre_archivo}", mime)

                nuevo_logo = {
                    "id": int(datetime.now().timestamp()),
                    "cliente": nombre_cliente,
                    "nombre": nombre_logo,
                    "precio_usd": 5.0,
                    "precio_dop": 300.0,
                    "estado": "Pendiente",
                    "pago": "Pendiente",
                    "tipo": tipo_aplicacion,
                    "ubicacion_gorra": ubicacion_gorra,
                    "detalle_gorra": detalle_gorra,
                    "comentario": comentario_cliente if comentario_cliente else "Ninguno",
                    "archivo": nombre_archivo,
                    "imagen_bytes": img_bytes,
                    "gdrive_url": url_drive
                }

                # 1. Guardar primero en Supabase
                guardar_logo_supabase(nuevo_logo)

                # 2. Recargar datos de la BD en la sesión
                st.session_state.logos = cargar_datos_supabase()

                st.success("✅ ¡Orden guardada en la base de datos!")
                st.rerun()

            except Exception as e:
                st.error(f"Error procesando la solicitud: {e}")

st.divider()

# --- HISTORIAL RECUPERADO DE SUPABASE ---
st.subheader("📋 Mis Pedidos Registrados")
mis_ordenes = [l for l in st.session_state.logos if l.get('cliente') == nombre_cliente]

if not mis_ordenes:
    st.info("No tienes solicitudes guardadas en el sistema.")
else:
    for o in mis_ordenes:
        st.markdown(f"**🧵 {o.get('nombre')}** — Estado: `{o.get('estado')}`")
        if o.get('gdrive_url'):
            st.markdown(f"[📁 Ver archivo en Google Drive]({o.get('gdrive_url')})")
        st.divider()
