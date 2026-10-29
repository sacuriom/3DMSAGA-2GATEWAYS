# Actualización de Ruta 4 — C27-0810

Esta revisión incorpora la repetición del 27 de octubre, 08:10–09:26 (Ecuador UTC−5), y conserva por separado la ventana original sin datos del día anterior. La publicación remota y la licencia del código propio siguen pendientes.

## Resultados comprobables

- Los dos archivos completos contienen 483 ensayos y 383 recepciones TTS. La ventana declarada contiene 432 ensayos, 332 con TTS: 76,8519 %. Se excluyen del porcentaje veinte registros anteriores y treinta y uno posteriores, conservándolos en las fuentes.
- Paltas recibe 256; PUCESA, 211; ambos, 135. Solo Paltas: 121; solo PUCESA: 76. Se describe complementariedad observada, sin un ensayo causal de desconexión de gateways.
- Solo 181 de 432 ensayos tienen GPS; el último es de 08:41:51. El segundo archivo no contiene ninguna posición. No se interpolan coordenadas, no se utiliza el plan de Maps como trayectoria real y no se toma la posición del gateway como ubicación del FT.
- Hay 44 candidatos de calle próximos a posiciones válidas y 35 con señal asociada a 45 m, a partir de 69 ensayos recibidos. El máximo calibrado congelado tiene RMSE 23,8524 dB, MAE 22,7314 dB y 1/35 dentro de ±6 dB. El máximo original tiene RMSE 22,1477 dB: el ajuste global histórico no mejora este nuevo contraste.
- La versión congelada coincide por SHA-256 con el dataset usado antes; no se vuelven a ajustar coeficientes. La diferencia frente a 11,7647 dB en C26-1400 no se trata como comparación controlada de la misma población.

## Fuentes y reproducción

`data/field_20261027/fuentes/`: dos CSV originales byte a byte. `extraccion_tts/`: respuesta HTTP200, manifiesto y código de extracción sin credencial. La consulta recuperó 385 registros, 383 de prueba y dos fuera del patrón; no alcanzó el límite de 1000 ni produjo errores de parseo. El payload de prueba no aporta coordenadas con las que sustituir GNSS ausente.

`resultados/`: ensayos completos y seleccionados, correspondencias FCnt, metadatos por receptor, asociaciones de posición, sensibilidad 15/30/45/60 m y medianas por candidato. `campaign_metadata.json` conserva el horario y la declaración del investigador: el FT permaneció en la parrilla y pararon para reubicar una antena desplazada. No se conoce el instante exacto ni se atribuye causalidad a esa intervención.

Comprobación independiente, solo biblioteca estándar: `python scripts/verify_release.py`. Incluye ambas fechas y contrasta las posiciones/candidatos de Ruta 4 mediante una reconstrucción Haversine independiente. El modo MATLAB por defecto sigue apuntando a C26-1400; no se cambia silenciosamente esa cohorte.

Recálculo del análisis completo con numpy:

```sh
python scripts/auditar_ruta4_27oct.py --campaign-root data/field_20261027 --frozen-dataset src/matlab/datos/nodos_referencia.csv --prior-network data/field_model_comparison/red_mejor_enlace_intersecciones_sin_anclas.csv --output outputs/ruta4_recalculada
```

Figura vectorial con reportlab: `python scripts/generar_figura_ruta4.py`. Las dependencias de análisis, opcionales para verificar la entrega, constan en requirements-analysis.txt y sus versiones usadas en verification/analysis_runtime.json. CI verifica sin instalar esas bibliotecas.

Los offsets de FCnt +1316/+1713 son específicos de estos archivos. Hay un intervalo de 45 s entre ambos; no se inventan ensayos para rellenarlo. La sesión de red no se reconstruye solo a partir del reinicio del contador local. La mediana FT menos radio de 9,2585 s verifica concordancia temporal, sin acreditar la semántica del GNSS.

La nueva campaña añade 30 candidatos con señal respecto de los 182 de las tres ventanas anteriores: la unión espacial es 212. No se suman RMSE ni se mezclan ambas cohortes como réplicas intercambiables. Las alturas, ganancias, potencia física y calidad temporal siguen siendo limitaciones documentadas.
