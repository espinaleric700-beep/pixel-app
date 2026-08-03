import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import os
import io
import base64
from supabase import create_client, Client

# --- LIBRERÍAS DE GOOGLE DRIVE Y CUENTA DE SERVICIO ---
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

# --- FUNCIÓN PARA SUBIR ARCHIVOS A GOOGLE DRIVE (SERVICE ACCOUNT) ---
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
        st.error(f"⚠️ Error al subir a Google Drive: {e}")
        return None

# --- CONVERTIR LOGO A BASE64 PARA EL FONDO ---
logo_path = "PIXEL THREAD W_Mesa de trabajo 1_2.jpg"
logo_base64 = ""
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(135deg, rgba(10, 15, 29, 0.93) 0%, rgba(17, 24, 39, 0.93) 50%, rgba(31, 17, 40, 0.93) 100%);
        color: #e2e8f0;
    }}
    
    .stApp::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60vw;
        height: 60vw;
        max-width: 650px;
        max-height: 650px;
        background-image: url("data:image/jpeg;base64,{logo_base64}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.08;
        z-index: 0;
        pointer-events: none;
    }}

    div[data-testid="stExpander"], div.stContainer, div[data-testid="stVerticalBlock"] > div > div.element-container {{
        position: relative;
        z-index: 1;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(17, 24, 39, 0.85);
        border: 1px solid rgba(0, 255, 204, 0.2);
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 0 15px rgba(0, 255, 204, 0.05);
    }}

    .stButton>button {{
        background: linear-gradient(90deg, #00ffcc 0%, #0077ff 100%);
        color: #0a0f1d;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0, 255, 204, 0.3);
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.6);
        transform: translateY(-2px);
    }}

    section[data-testid="stSidebar"] {{
        background-color: #070a14;
        border-right: 1px solid rgba(0, 255, 204, 0.1);
    }}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE PERSISTENCIA CON SUPABASE ---
def cargar_datos_supabase():
    if not supabase:
        return None, None
    try:
        res_clientes = supabase.table("clientes_registrados").select("*").execute()
        clientes_dict = {}
        if res_clientes.data:
            for row in res_clientes.data:
                avatar_bytes = base64.b64decode(row["avatar_bytes"].encode("utf-8")) if row.get("avatar_bytes") else None
                clientes_dict[row["nombre"]] = {
                    "divisa": row.get("divisa", "Dólares (USD - $)"),
                    "avatar_bytes": avatar_bytes,
                    "avatar_nombre": row.get("avatar_nombre")
                }

        res_logos = supabase.table("logos").select("*").execute()
        logos_list = []
        if res_logos.data:
            for row in res_logos.data:
                img_bytes = None
                if row.get("imagen_bytes"):
                    try:
                        img_bytes = base64.b64decode(row["imagen_bytes"].encode("utf-8"))
                    except Exception:
                        img_bytes = None

                logos_list.append({
                    "id": row["id"],
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
                    "archivos_multiples": row.get("archivos_multiples", []),
                    "gdrive_url": row.get("gdrive_url")
                })
        
        return clientes_dict, logos_list
    except Exception as e:
        st.error(f"Error cargando desde Supabase: {e}")
        return None, None

def guardar_cliente_supabase(nombre, divisa, avatar_bytes=None, avatar_nombre=None):
    if not supabase:
        return
    avatar_b64 = base64.b64encode(avatar_bytes).decode("utf-8") if avatar_bytes else None
    supabase.table("clientes_registrados").upsert({
        "nombre": nombre,
        "divisa": divisa,
        "avatar_bytes": avatar_b64,
        "avatar_nombre": avatar_nombre
    }).execute()

def eliminar_cliente_supabase(nombre):
    if not supabase:
        return
    supabase.table("clientes_registrados").delete().eq("nombre", nombre).execute()
    supabase.table("logos").delete().eq("cliente", nombre).execute()

def guardar_logo_supabase(logo_dict):
    if not supabase:
        return
    # Preparamos una copia serializable limpia para Supabase
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
        "gdrive_url": logo_dict.get("gdrive_url")
    }
    
    # Convertir bytes a base64 string seguro para JSON/Supabase
    if logo_dict.get("imagen_bytes"):
        logo_db["imagen_bytes"] = base64.b64encode(logo_dict["imagen_bytes"]).decode("utf-8")
    else:
        logo_db["imagen_bytes"] = None

    supabase.table("logos").upsert(logo_db).execute()

# --- BANDERAS Y ESTADO DE SESIÓN ---
if "sesion_activa" not in st.session_state:
    st.session_state.sesion_activa = None  

# Cargar datos iniciales
if "clientes_registrados" not in st.session_state or "logos" not in st.session_state:
    clientes_db, logos_db = cargar_datos_supabase()
    st.session_state.clientes_registrados = clientes_db if clientes_db is not None else {
        "Cliente A": {"divisa": "Dólares (USD - $)", "avatar_bytes": None, "avatar_nombre": None},
        "Cliente B": {"divisa": "Pesos Dominicanos (DOP - RD$)", "avatar_bytes": None, "avatar_nombre": None}
    }
    st.session_state.logos = logos_db if logos_db is not None else []

# Autorefresh global
st_autorefresh(interval=5000, limit=None, key="autorefresh_global")

# --- MENÚ LATERAL ---
st.sidebar.title("Pixel Thread 🧵")

if st.session_state.sesion_activa is None:
    st.sidebar.subheader("🔒 Iniciar Sesión")
    tipo_ingreso = st.sidebar.radio("Tipo de Acceso", ["Cliente", "Panel Administrador"])
    
    if tipo_ingreso == "Panel Administrador":
        pin_ingresado = st.sidebar.text_input("Contraseña Administrador", type="password")
        if st.sidebar.button("Entrar como Admin"):
            if pin_ingresado == "2580PIXEL":
                st.session_state.sesion_activa = "admin"
                st.success("¡Acceso concedido!")
                st.rerun()
            else:
                st.error("Contraseña incorrecta. Usa: 2580PIXEL")
    else:
        usuario_ingresado = st.sidebar.text_input("Ingresa tu Nombre de Usuario")
        if st.sidebar.button("Entrar a mi Portal"):
            if usuario_ingresado in st.session_state.clientes_registrados:
                st.session_state.sesion_activa = usuario_ingresado
                st.success(f"¡Bienvenido, {usuario_ingresado}!")
                st.rerun()
            else:
                st.error("Usuario no encontrado.")
    st.stop()

else:
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.sesion_activa = None
        st.rerun()
    
    st.sidebar.divider()
    st.sidebar.success(f"👤 Sesión: {st.session_state.sesion_activa}")

# ==========================================
# 1. VISTA ADMINISTRADOR
# ==========================================
if st.session_state.sesion_activa == "admin":
    st.title("🎛️ Panel de Control - Pixel Thread")
    
    total_usd = sum(l.get('precio_usd', 5.0) for l in st.session_state.logos if l.get('estado') == "Terminado")
    total_dop = sum(l.get('precio_dop', 300.0) for l in st.session_state.logos if l.get('estado') == "Terminado")
    
    col1, col2 = st.columns(2)
    col1.metric("Acumulado (USD)", f"${total_usd:.2f} USD")
    col2.metric("Acumulado (DOP)", f"RD$ {total_dop:,.2f}")

    st.divider()

    st.subheader("📋 Pedidos Recibidos")
    if not st.session_state.logos:
        st.info("No hay órdenes registradas.")
    else:
        for idx, logo in enumerate(st.session_state.logos, 1):
            with st.expander(f"Orden #{idx} - {logo.get('nombre')} ({logo.get('cliente')}) - {logo.get('estado')}", expanded=True):
                col_img, col_det = st.columns([1, 3])
                with col_img:
                    if logo.get('imagen_bytes'):
                        try:
                            st.image(Image.open(io.BytesIO(logo['imagen_bytes'])), width=120)
                        except Exception:
                            st.caption("📷 Imagen cargada")
                    else:
                        st.caption("Sin imagen")
                with col_det:
                    st.write(f"**Cliente:** {logo.get('cliente')}")
                    st.write(f"**Soporte:** {logo.get('tipo')} | **Ubicación:** {logo.get('ubicacion_gorra')}")
                    st.write(f"**Instrucciones:** {logo.get('comentario')}")
                    if logo.get('gdrive_url'):
                        st.markdown(f"[📁 Abrir Archivo en Google Drive]({logo.get('gdrive_url')})")

# ==========================================
# 2. VISTA PORTAL CLIENTE
# ==========================================
else:
    nombre_cliente = st.session_state.sesion_activa
    st.title(f"Portal de Cliente: {nombre_cliente}")

    # --- FORMULARIO FIJO DE NAVEGACIÓN ---
    st.subheader("📤 Enviar Nuevo Logo a Digitalizar")
    
    with st.form(key=f"form_envio_logo_{nombre_cliente}", clear_on_submit=True):
        nombre_logo = st.text_input("Nombre del Logo / Diseño *")
        archivos_subidos = st.file_uploader("Sube tu archivo (PNG, JPG, PDF, AI)", type=["png", "jpg", "jpeg", "ai", "pdf"], accept_multiple_files=False)
        tipo_aplicacion = st.radio("Soporte del bordado:", ["Tela (Camisetas, Polos, etc.)", "Gorra"])
        
        ubicacion_gorra = "N/A"
        detalle_gorra = "N/A"
        if tipo_aplicacion == "Gorra":
            ubicacion_gorra = st.radio("Ubicación:", ["Frontal", "Trasero", "Lateral"])
            detalle_gorra = st.radio("Estilo:", ["3D (Puff)", "Plano (Flat)"]) if ubicacion_gorra == "Frontal" else "Plano (Flat)"
        
        comentario_cliente = st.text_area("Instrucciones especiales")
        
        btn_enviar = st.form_submit_button("🚀 ENVIAR LOGO A PIXEL THREAD")

    if btn_enviar:
        if not nombre_logo.strip():
            st.error("❌ Por favor escribe el nombre del logo.")
        else:
            with st.spinner("⏳ Procesando y guardando orden..."):
                try:
                    img_bytes_guardar = None
                    nombre_archivo_orig = "Sin archivo"
                    url_gdrive = None

                    if archivos_subidos is not None:
                        img_bytes_guardar = archivos_subidos.getvalue()
                        nombre_archivo_orig = archivos_subidos.name
                        tipo_mime = archivos_subidos.type or "application/octet-stream"

                        # 1. Intentar Subir a Google Drive
                        url_gdrive = subir_a_google_drive(
                            img_bytes_guardar, 
                            f"{nombre_cliente}_{nombre_logo}_{nombre_archivo_orig}", 
                            mime_type=tipo_mime
                        )

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
                        "archivo": nombre_archivo_orig,
                        "imagen_bytes": img_bytes_guardar,
                        "gdrive_url": url_gdrive
                    }

                    # 2. Guardar en Supabase
                    guardar_logo_supabase(nuevo_logo)

                    # 3. Guardar en estado local de sesión
                    st.session_state.logos.append(nuevo_logo)

                    st.success("🎉 ¡Logo subido y registrado con éxito!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al procesar la orden: {e}")

    st.divider()

    # --- HISTORIAL DE PEDIDOS EN EL PORTAL DE CLIENTE ---
    st.subheader("📋 Mis Pedidos Registrados")
    mis_logos = [l for l in st.session_state.logos if l.get('cliente') == nombre_cliente]
    
    if not mis_logos:
        st.info("Aún no has enviado ningún logo.")
    else:
        for l in mis_logos:
            with st.container():
                col_a, col_b = st.columns([1, 3])
                with col_a:
                    if l.get('imagen_bytes'):
                        try:
                            st.image(Image.open(io.BytesIO(l['imagen_bytes'])), width=90)
                        except Exception:
                            st.caption("🖼️ Imagen subida")
                    else:
                        st.caption("Sin miniatura")
                with col_b:
                    st.markdown(f"**🧵 {l.get('nombre')}** — Estado: `{l.get('estado')}`")
                    st.write(f"Soporte: {l.get('tipo')} | Comentario: {l.get('comentario')}")
                    if l.get('gdrive_url'):
                        st.markdown(f"[📁 Ver en Google Drive]({l.get('gdrive_url')})")
            st.divider()