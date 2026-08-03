if st.form_submit_button("Guardar Cambios"):
                            logo['nombre'] = nuevo_nombre
                            logo['comentario'] = nuevo_comentario
                            guardar_datos()
                            st.success("¡Orden modificada con éxito!")
                            st.rerun()
            with col_elim:
                if st.button("🗑️ Cancelar / Eliminar", key=f"del_{logo['id']}"):
                    st.session_state.logos = [l for l in st.session_state.logos if l.get('id') != logo['id']]
                    guardar_datos()
                    st.warning("¡La orden ha sido eliminada!")
                    st.rerun()

        elif estado_logo == "En Revisión":
            st.warning("🔍 Tu diseño se encuentra en revisión por el equipo técnico.")
        elif estado_logo == "En Progreso":
            st.success("🟢 ¡Manos a la obra! Tu diseño está siendo digitalizado en este momento.")

        st.divider()

    # TRABAJOS REALIZADOS Y DESCARGA DE ARCHIVOS FINALES
    st.subheader("✅ Trabajos Realizados y Descarga de Archivos")
    if not logos_realizados:
        st.info("No tienes trabajos terminados listos para descargar todavía.")

    for logo in logos_realizados:
        col_img, col_info = st.columns([1, 3])
        with col_img:
            if logo.get('imagen_bytes'):
                try:
                    img_cargada = Image.open(io.BytesIO(logo['imagen_bytes']))
                    st.image(img_cargada, caption=logo.get('nombre', 'Diseño'), width=100)
                except Exception:
                    st.info("Sin miniatura")
            elif logo.get('imagen_obj') is not None:
                st.image(logo['imagen_obj'], caption=logo.get('nombre', 'Diseño'), width=100)
            else:
                st.info("Sin miniatura")
                
        with col_info:
            st.markdown(f"### 🧵 {logo.get('nombre', 'Logo')} — <span style='color: #00ffcc;'>¡Terminado!</span>", unsafe_allow_html=True)
            st.write(f"**Aplicación:** {logo.get('tipo', 'Tela')} | **Ubicación:** {logo.get('ubicacion_gorra', 'N/A')} | **Estilo:** {logo.get('detalle_gorra', 'N/A')}")
            
            p_usd = logo.get('precio_usd', 5.0)
            p_dop = logo.get('precio_dop', 300.0)
            if "Dólares" in divisa:
                st.write(f"**Precio:** ${p_usd:.2f} USD | **Estado de Pago:** `{logo.get('pago', 'Pendiente')}`")
            else:
                st.write(f"**Precio:** RD$ {p_dop:,.2f} DOP | **Estado de Pago:** `{logo.get('pago', 'Pendiente')}`")

            # Sección de descarga de archivos múltiples subidos por el admin
            archivos_multiples = logo.get('archivos_multiples', [])
            if archivos_multiples:
                st.markdown("📥 **Archivos de bordado listos para descargar:**")
                for arch_info in archivos_multiples:
                    st.download_button(
                        label=f"⬇️ Descargar `{arch_info['nombre']}`",
                        data=arch_info['bytes'],
                        file_name=arch_info['nombre'],
                        mime="application/octet-stream",
                        key=f"dl_final_{logo['id']}_{arch_info['nombre']}"
                    )
            else:
                st.info("⏳ Los archivos finales (.DST/.EMB/.PDF) estarán disponibles pronto.")

        st.divider()
