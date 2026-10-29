# Sustento de la sección 3.7 — 28-10-2026

## Uso recomendado

1. Un gateway: `data/single_gateway_legacy/auditar_campo.py` reproduce las métricas conservadas. La suite MATLAB archivada y el predictor no demuestran por sí mismos una validación independiente; no hay exportación cruda completa incluida para repetir toda la ingesta local.
2. Dos gateways: `scripts/extraer_tts_verificable.py` conserva captura TTS; `scripts/verify_release.py` reconstruye el cruce desde fuentes. Consultar su ayuda antes de una descarga. No requiere credencial para verificar offline.
3. MATLAB: `src/matlab/config_campana_ambato.m`, `MDPI_3DMSAGA_Trazable.m` y `verificar_revision.m` son la entrada de auditoría C26-1400. El modo físico se detiene si faltan parámetros. No se cambian los datos para obtener mejores métricas.
4. Ruta 4 del 27: procedimiento separado en `scripts/auditar_ruta4_27oct.py` y `scripts/verify_route4.py`. Ver `RUTA4_27OCT.md`.

`SELECCION_MATLAB_CAP3.csv` identifica cada archivo. Los originales integrados se conservan en `src/matlab_original_reference`, no como ejecutables recomendados para generar nuevas conclusiones. Las rutas absolutas y los parámetros heredados se conservan como evidencia histórica y limitan su portabilidad. El modo de ingesta histórico no se usa en la comprobación principal. Se reemplaza su credencial por `getenv('TTS_API_KEY')`; no se modifica el original privado.

## Cambios de tesis

`SECCION_3_7_TESIS.tex` reemplaza la sección completa. Se documentan etapas 1GW/2GW, identidad de receptores, sesiones/contadores, datos sin GNSS, radios de asociación por versión, métricas, sesgo de selección y separación ajuste/evaluación. Se retira la afirmación de que 70% dentro de ±6 dB valida estadísticamente el predictor. Se elimina en la copia completa la segunda sección ética que duplicaba la etiqueta sec:Cap3.7.

El texto pegado recibido contiene versiones antiguas también en resumen, modelo RF, hipótesis, resultados y conclusiones. Esta revisión no armoniza esos capítulos ni acredita las afirmaciones sobre difracción UIT-R, optimalidad, inmunidad a fallos o PDR 94,27%. No sustituir el proyecto completo vigente por la copia recibida: integrar la sección 3.7 en la versión más reciente.

## Publicación

La API de GitHub informó que el repositorio remoto estaba vacío al revisarlo. Esta entrega es una selección local para cargar, sin commit remoto. La licencia permanece pendiente según LICENSE_PENDING.md. La existencia de archivos preparados no acredita su disponibilidad remota.
