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
    """
    Sube un archivo a Google Drive usando las credenciales de la Cuenta de Servicio.
    """
    try:
        # Carga las credenciales desde los secrets de Streamlit (formato JSON de Service Account)
        creds_dict = st.secrets["gserviceaccount"]
        scopes = ["https://www.googleapis.com/auth/drive"]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)

        # ID de la carpeta compartida en Google Drive (Opcional pero recomendado)
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
        st.error(f"Error subiendo archivo a Google Drive: {e}")
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
    div[data-testid="stMetric"] label {{
        color: #94a3b8 !important;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: #00ffcc !important;
        text-shadow: 0 0 10px rgba(0, 255, 204, 0.4);
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
        # Cargar clientes
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

        # Cargar logos
        res_logos = supabase.table("logos").select("*").execute()
        logos_list = []
        if res_logos.data:
            for row in res_logos.data:
                img_bytes = base64.b64decode(row["imagen_bytes"].encode("utf-8")) if row.get("imagen_bytes") else None
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
        st.error(f"Error conectando con Supabase: {e}")
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
    logo_db = logo_dict.copy()
    if logo_db.get("imagen_bytes"):
        logo_db["imagen_bytes"] = base64.b64encode(logo_db["imagen_bytes"]).decode("utf-8")
    
    if "imagen_obj" in logo_db:
        del logo_db["imagen_obj"]

    supabase.table("logos").upsert(logo_db).execute()

def eliminar_logo_supabase(logo_id):
    if not supabase:
        return
    supabase.table("logos").delete().eq("id", logo_id).execute()

# --- ACTUALIZACIÓN AUTOMÁTICA CADA 2 SEGUNDOS ---
st_autorefresh(interval=2000, limit=None, key="autorefresh_global")

# --- CARGAR DATOS DESDE SUPABASE AL INICIAR LA SESIÓN ---
clientes_db, logos_db = cargar_datos_supabase()

if "clientes_registrados" not in st.session_state:
    if clientes_db:
        st.session_state.clientes_registrados = clientes_db
    else:
        st.session_state.clientes_registrados = {
            "Cliente A": {"divisa": "Dólares (USD - $)", "avatar_bytes": None, "avatar_nombre": None},
            "Cliente B": {"divisa": "Pesos Dominicanos (DOP - RD$)", "avatar_bytes": None, "avatar_nombre": None}
        }

if "logos" not in st.session_state:
    if logos_db:
        st.session_state.logos = logos_db
    else:
        st.session_state.logos = [
            {"id": 1, "cliente": "Cliente A", "nombre": "Logo León Dorado", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "Pendiente", "pago": "Pendiente", "tipo": "Tela", "ubicacion_gorra": "N/A", "detalle_gorra": "N/A", "comentario": "Urgente", "archivo": "leon.png"},
            {"id": 2, "cliente": "Cliente A", "nombre": "Logo Cafetería", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "En Revisión", "pago": "Pendiente", "tipo": "Gorra", "ubicacion_gorra": "Frontal", "detalle_gorra": "3D (Puff)", "comentario": "Centrado", "archivo": "cafe.png"},
            {"id": 3, "cliente": "Cliente B", "nombre": "Escudo Deportivo", "precio_usd": 5.0, "precio_dop": 300.0, "estado": "Terminado", "pago": "Pagado", "tipo": "Tela", "ubicacion_gorra": "N/A", "detalle_gorra": "N/A", "comentario": "Ninguno", "archivo": "escudo.png"},
        ]

if "recibos_pago" not in st.session_state:
    st.session_state.recibos_pago = {}

if "form_enviado" not in st.session_state:
    st.session_state.form_enviado = False

# Control de sesión segura
if "sesion_activa" not in st.session_state:
    st.session_state.sesion_activa = None  

# --- MENÚ DE NAVEGACIÓN Y AUTENTICACIÓN LATERAL ---
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
                st.error("Usuario no encontrado o no autorizado. Solicítalo al administrador.")
    
    st.sidebar.divider()
    st.sidebar.info("💡 Tarifa oficial: $5.00 USD / $300.00 DOP por logo digitalizado.")
    st.stop()

else:
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.sesion_activa = None
        st.rerun()
    
    st.sidebar.divider()
    if st.session_state.sesion_activa == "admin":
        st.sidebar.success("🔑 Sesión Activa: Administrador")
    else:
        st.sidebar.success(f"👤 Sesión Activa: {st.session_state.sesion_activa}")
    
    st.sidebar.divider()
    st.sidebar.info("💡 Tarifa oficial: $5.00 USD / $300.00 DOP por logo digitalizado.")
    st.sidebar.caption("🔄 Actualización automática, Supabase y Drive activos")

# ==========================================
# 1. VISTA ADMINISTRADOR
# ==========================================
if st.session_state.sesion_activa == "admin":
    st.title("🎛️ Panel de Control - Pixel Thread")
    st.write("Administra el flujo de trabajo industrial, el estado de pagos y la entrega de archivos de bordado (.DST/.EMB/.PDF).")

    total_usd = sum(l.get('precio_usd', 5.0) for l in st.session_state.logos if l.get('estado', 'Pendiente') == "Terminado" and l.get('estado') != "Archivado/Pagado")
    total_dop = sum(l.get('precio_dop', 300.0) for l in st.session_state.logos if l.get('estado', 'Pendiente') == "Terminado" and l.get('estado') != "Archivado/Pagado")
    
    col1, col2 = st.columns(2)
    col1.metric("Total Acumulado (Semana)", f"${total_usd:.2f} USD")
    col2.metric("Total Acumulado (Semana)", f"RD$ {total_dop:,.2f}")

    st.divider()

    with st.expander("➕ Registrar Nuevo Cliente, Control y Recibos"):
        st.subheader("➕ Registrar Nuevo Cliente y su Divisa")
        with st.form(key="form_nuevo_cliente"):
            col_nc1, col_nc2 = st.columns(2)
            with col_nc1:
                nuevo_nombre_cli = st.text_input("Nombre de Usuario del Cliente (Ej. Cliente C)")
                nueva_divisa_cli = st.selectbox("Moneda Principal / Divisa", ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"])
            with col_nc2:
                avatar_nuevo_file = st.file_uploader("Logo / Avatar del Cliente (Opcional)", type=["png", "jpg", "jpeg"])
            
            btn_crear_cli = st.form_submit_button("Registrar Cliente")
            if btn_crear_cli:
                if nuevo_nombre_cli:
                    if nuevo_nombre_cli in st.session_state.clientes_registrados:
                        st.error("¡Este cliente ya está registrado!")
                    else:
                        avatar_bytes_val = avatar_nuevo_file.getvalue() if avatar_nuevo_file else None
                        avatar_nombre_val = avatar_nuevo_file.name if avatar_nuevo_file else None

                        st.session_state.clientes_registrados[nuevo_nombre_cli] = {
                            "divisa": nueva_divisa_cli,
                            "avatar_bytes": avatar_bytes_val,
                            "avatar_nombre": avatar_nombre_val
                        }
                        guardar_cliente_supabase(nuevo_nombre_cli, nueva_divisa_cli, avatar_bytes_val, avatar_nombre_val)
                        st.success(f"¡Cliente '{nuevo_nombre_cli}' agregado con éxito en Supabase!")
                        st.rerun()
                else:
                    st.error("Por favor, ingresa un nombre para el cliente.")

        st.divider()

        st.subheader("👥 Control, Cierre de Ciclo y Gestión de Clientes")
        for cli in list(st.session_state.clientes_registrados.keys()):
            logos_cli_term = [l for l in st.session_state.logos if l.get('cliente') == cli and l.get('estado', 'Pendiente') == "Terminado"]
            sub_usd = sum(l.get('precio_usd', 5.0) for l in logos_cli_term)
            sub_dop = sum(l.get('precio_dop', 300.0) for l in logos_cli_term)
            
            with st.expander(f"👤 Cliente: {cli} — Acumulado Terminado: ${sub_usd:.2f} USD / RD$ {sub_dop:,.2f}"):
                c_info, c_btn_reset, c_btn_del = st.columns([2, 1, 1])
                with c_info:
                    st.write(f"Trabajos terminados pendientes de cerrar ciclo: **{len(logos_cli_term)}**")
                with c_btn_reset:
                    if st.button(f"🔄 Reiniciar Ciclo", key=f"reset_cli_{cli}"):
                        for logo in st.session_state.logos:
                            if logo.get('cliente') == cli and logo.get('estado', 'Pendiente') == "Terminado":
                                logo['pago'] = "Pagado"
                                logo['estado'] = "Archivado/Pagado"
                                guardar_logo_supabase(logo)
                        st.success(f"¡Ciclo de {cli} reiniciado!")
                        st.rerun()
                with c_btn_del:
                    if st.button(f"🗑️ Eliminar Usuario", key=f"del_cli_{cli}"):
                        del st.session_state.clientes_registrados[cli]
                        if cli in st.session_state.recibos_pago:
                            del st.session_state.recibos_pago[cli]
                        st.session_state.logos = [l for l in st.session_state.logos if l.get('cliente') != cli]
                        eliminar_cliente_supabase(cli)
                        st.warning(f"¡Usuario '{cli}' eliminado de Supabase!")
                        st.rerun()

    st.divider()

    logos_activos_admin = [l for l in st.session_state.logos if l.get('estado') != "Archivado/Pagado"]
    logos_por_hacer = [l for l in logos_activos_admin if l.get('estado', 'Pendiente') != "Terminado"]
    logos_terminados = [l for l in logos_activos_admin if l.get('estado', 'Pendiente') == "Terminado"]

    st.subheader("📋 Gestión de Trabajos Activos")
    if not logos_por_hacer:
        st.info("No hay trabajos activos pendientes o en proceso.")

    for idx_cola, logo in enumerate(logos_por_hacer, 1):
        i = st.session_state.logos.index(logo)
        with st.container():
            col_img, col_info = st.columns([1, 3])
            with col_img:
                if logo.get('imagen_bytes'):
                    try:
                        st.image(Image.open(io.BytesIO(logo['imagen_bytes'])), caption="Diseño", width=100)
                    except:
                        st.info("Sin miniatura")
                else:
                    st.info("Sin miniatura")

            with col_info:
                st.markdown(f"### 🔢 Cola #{idx_cola} - 🧵 {logo.get('nombre')} *({logo.get('cliente')})*")
                st.write(f"**Tipo:** {logo.get('tipo')} | **Ubicación:** {logo.get('ubicacion_gorra')} | **Estilo:** {logo.get('detalle_gorra')}")
                st.write(f"**Comentario:** {logo.get('comentario')}")
                st.write(f"**Precio:** ${logo.get('precio_usd', 5.0):.2f} USD")
                if logo.get('gdrive_url'):
                    st.markdown(f"[📁 Ver enlace en Google Drive]({logo.get('gdrive_url')})")
            
            estado_actual = logo.get('estado', 'Pendiente')
            c1, c2, c3 = st.columns(3)
            
            if estado_actual == "Pendiente":
                if c1.button("🔍 Pasar a Revisión", key=f"rev_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "En Revisión"
                    guardar_logo_supabase(st.session_state.logos[i])
                    st.rerun()
            elif estado_actual == "En Revisión":
                if c2.button("▶ Iniciar (Luz Verde)", key=f"iniciar_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "En Progreso"
                    guardar_logo_supabase(st.session_state.logos[i])
                    st.rerun()
            elif estado_actual == "En Progreso":
                if c2.button("✓ Marcar Terminado", key=f"terminar_{logo['id']}"):
                    st.session_state.logos[i]['estado'] = "Terminado"
                    guardar_logo_supabase(st.session_state.logos[i])
                    st.rerun()
        st.divider()

    st.subheader("✅ Trabajos Ya Realizados")
    for logo in logos_terminados:
        i = st.session_state.logos.index(logo)
        st.markdown(f"**🧵 {logo.get('nombre')}** - Cliente: {logo.get('cliente')}")
        pago_actual = logo.get('pago', 'Pendiente')
        nuevo_pago = st.selectbox("Estado de Pago", ["Pendiente", "Pagado"], index=0 if pago_actual=="Pendiente" else 1, key=f"pago_{logo['id']}")
        if nuevo_pago != pago_actual:
            st.session_state.logos[i]['pago'] = nuevo_pago
            guardar_logo_supabase(st.session_state.logos[i])
            st.rerun()
        st.divider()

# ==========================================
# 2. VISTA PORTAL DE CLIENTES
# ==========================================
else:
    nombre_cliente = st.session_state.sesion_activa
    info_cliente = st.session_state.clientes_registrados.get(nombre_cliente, {"divisa": "Dólares (USD - $)", "avatar_bytes": None})
    divisa_default = info_cliente.get("divisa", "Dólares (USD - $)") if isinstance(info_cliente, dict) else info_cliente
    avatar_bytes = info_cliente.get("avatar_bytes", None) if isinstance(info_cliente, dict) else None

    col_av, col_tit = st.columns([1, 12])
    with col_av:
        if avatar_bytes:
            try:
                st.image(Image.open(io.BytesIO(avatar_bytes)), width=55)
            except:
                st.markdown("👤")
        else:
            st.markdown("👤")
    with col_tit:
        st.title(f"Portal de Cliente: {nombre_cliente}")

    divisa = st.radio("Selecciona tu moneda:", ["Dólares (USD - $)", "Pesos Dominicanos (DOP - RD$)"], index=0 if "Dólares" in divisa_default else 1, horizontal=True)
    
    logos_cliente = [l for l in st.session_state.logos if l.get('cliente') == nombre_cliente and l.get('estado') != "Archivado/Pagado"]
    
    with st.popover("➕ Enviar Nuevo Logo", use_container_width=True):
        nombre_logo = st.text_input("Nombre del Logo / Diseño", key=f"inp_nom_{nombre_cliente}")
        archivos_subidos = st.file_uploader("Sube tus archivos originales", type=["png", "jpg", "jpeg", "ai", "pdf"], accept_multiple_files=True)
        tipo_aplicacion = st.radio("Soporte del bordado:", ["Tela (Camisetas, Polos, etc.)", "Gorra"])
        
        ubicacion_gorra, detalle_gorra = "N/A", "N/A"
        if tipo_aplicacion == "Gorra":
            ubicacion_gorra = st.radio("Ubicación:", ["Frontal", "Trasero", "Lateral"])
            detalle_gorra = st.radio("Estilo:", ["3D (Puff)", "Plano (Flat)"]) if ubicacion_gorra == "Frontal" else "Plano (Flat)"
        
        comentario_cliente = st.text_area("Instrucciones especiales")
        
        if st.button("Enviar Logo a Pixel Thread"):
            if nombre_logo:
                img_bytes_guardar = archivos_subidos[0].getvalue() if archivos_subidos else None
                url_gdrive = None

                # --- SUBIR A GOOGLE DRIVE SI HAY ARCHIVO ---
                if img_bytes_guardar and archivos_subidos:
                    with st.spinner("Subiendo respaldo a Google Drive..."):
                        tipo_mime = archivos_subidos[0].type or "application/octet-stream"
                        url_gdrive = subir_a_google_drive(
                            img_bytes_guardar, 
                            f"{nombre_cliente}_{nombre_logo}_{archivos_subidos[0].name}", 
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
                    "archivo": archivos_subidos[0].name if archivos_subidos else "Sin archivo",
                    "imagen_bytes": img_bytes_guardar,
                    "gdrive_url": url_gdrive # <--- Guardamos la URL de Google Drive
                }
                st.session_state.logos.append(nuevo_logo)
                guardar_logo_supabase(nuevo_logo)
                
                if url_gdrive:
                    st.success(f"¡Orden y respaldo guardados en Google Drive con éxito!")
                else:
                    st.success("¡Orden guardada en Supabase con éxito!")
                st.rerun()
            else:
                st.error("Ingresa un nombre para el logo.")