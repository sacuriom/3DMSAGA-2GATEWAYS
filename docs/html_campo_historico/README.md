# HTML históricos de campo: apéndices B y C

Destino: https://github.com/sacuriom/3DMSAGA-2GATEWAYS

## Consulta

Abrir `dashboard_fieldtester.html` o `mapa_cobertura_lorawan.html` en un navegador, manteniendo toda esta carpeta. También puede servirse esta carpeta con `python -m http.server 8000` y abrir http://localhost:8000/dashboard_fieldtester.html. La vista de archivos de GitHub muestra código: no ejecuta estas páginas. No se ha activado GitHub Pages.

- Apéndice B: `dashboard_fieldtester.html` y `mapa_cobertura_lorawan.html`.
- Dependencias compartidas y navegación: `calles_ambato.js`, `dataset_fieldtester.js`, las páginas de rutas y sus datos JavaScript y CSV.
- Apéndice C: `verificacion_4rutas_cobertura.html` y `verificacion_4rutas_data.js`.

## Procedencia y alcance

Copias byte a byte de OCTUBRE; `manifest.json` contiene procedencia, tamaño y SHA-256. No se recalcularon los datos ni se modificaron las etiquetas históricas. No se presentan como una nueva extracción directa de TTS ni como una cohorte homogénea de la campaña de dos gateways.

El apéndice B describe una versión histórica del tablero de 64 archivos y más de 1460 observaciones. El HTML disponible contiene el encabezado «80 archivos analizados». No se recuperó en esta selección una versión HTML identificada como la de 64 archivos: no atribuir las cifras de la captura histórica a este archivo sin conciliar versiones y filtros. Se conserva el HTML hallado, sin alterar sus cifras para ajustarlas al texto.

Los términos de interfaz «PDR», «ACK», «cobertura» o «puntos ciegos» se conservan como etiquetas históricas. Por sí solos no certifican recepción uplink, fallos radioeléctricos ni cobertura continua. La visualización de intensidad no equivale a cobertura medida entre puntos. Los archivos reúnen distintas configuraciones y sesiones.

Los datos geográficos incluyen ubicaciones de campaña que el autor pidió documentar. Las bibliotecas de gráficos, mapas, fuentes y teselas se solicitan a servicios externos al abrir las páginas; estas visualizaciones requieren conectividad y no son completamente autónomas. Se conserva la atribución del mapa en los HTML. La lista de enlaces externos declarados figura en el manifiesto; las URL generadas dinámicamente pueden añadir solicitudes.

## Referencia en la tesis

Citar `repo_2gateways` y especificar `docs/html_campo_historico/` y el nombre del HTML. Al publicar, fijar un commit o etiqueta para identificar esta versión. La preparación local no acredita publicación remota ni activación de un sitio web.
