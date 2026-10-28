La carpeta conserva el contraste de 3D-M-SAGA en el sitio físico Paltas 0202 y Autachi, con un gateway UG67.

Ejecutar `python data/single_gateway_legacy/auditar_campo.py` desde el proyecto (o el mismo archivo desde cualquier directorio) para reproducir `Auditoria_campo_recalculada.json`, `Resumen_metricas_campo_recalculadas.csv` y `Desglose_4rutas_recalculado.csv`. Solo necesita Python 3 y su biblioteca estándar. No consulta Internet ni los archivos originales externos; utiliza las copias en `fuentes`.

Se recalculan tres cohortes: B.2 global SF9 (112 pares RSSI de 270 nodos visitados), C US915 SF7 20 dBm (49 pares) y la cohorte adicional Master US915 SF9 20 dBm (30 pares). La unión actual de nodos etiquetados Ruta 1 a Ruta 4 es 234 evaluados, 101 con RSSI, 133 sin RSSI. Las métricas emplean el residual empírico menos teórico, desviación poblacional y ventanas descriptivas ±6/±10 dB. La fracción de nodos con RSSI no es PDR de paquetes.

El predictor de campo se reconstruye independientemente de MATLAB para comprobar la fidelidad a los RSSI exportados. Master usa cota efectiva 2700 m y proyección local; el procesamiento global usa 2707 m y Haversine horizontal. En ambos casos la diferencia con el CSV no supera 0.005 dB, su precisión de exportación. Esta coincidencia comprueba la reproducción del modelo, no un error físico de 0.005 dB frente al campo.

`Procedencia_copias_campo.json` relaciona las copias con las rutas originales y sus SHA-256. La auditoría vuelve a calcular las huellas de todas las fuentes copiadas. Los scripts archivados `MDPI_FieldTester_Master_Suite.m` y `scratch_process_sf9.py` describen la ingestión y el predictor originales; su ejecución requiere el archivo local completo de la campaña y puede escribir resultados. Para revisar solo estas métricas debe utilizarse `auditar_campo.py`.

La transcripción B.1 (200 evaluados, 83 enlaces, 117 sin enlace, RMSE 13.14 dB, MAE 9.84 dB y similitud ±6 dB 39.8 %) se conserva de la tesis original. No se localizó el CSV exacto de aquella selección. También se mantienen como históricas las filas A (70 pares) y B (50 pares). No deben atribuirse a las cohortes reproducidas aquí.

El procesamiento histórico conserva el RSSI máximo por nodo; el predictor fue calibrado con la campaña y no hay partición reservada documentada. B.2 reúne campañas y potencias distintas. Es necesario interpretar estas características al utilizar las cifras en una publicación. La separación de RSSI ascendente/descendente y los contadores instrumentales completos se verifican con el archivo de campo local.

No se incluyen exportaciones crudas con claves de activación ni credenciales. Las copias de CSV son resultados derivados con coordenadas, indicadores de enlace y potencias, junto con los scripts sin claves.
