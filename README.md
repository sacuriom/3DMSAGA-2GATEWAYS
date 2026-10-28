# 3DMSAGA-2GATEWAYS

Entrega local preparada para https://github.com/sacuriom/3DMSAGA-2GATEWAYS. Separa observaciones del FT101, mensajes TTS y predicciones. Incluye la referencia de un gateway como cohorte historica y la extension Paltas-PUCESA; no las agrega como si compartieran condiciones.

```sh
python scripts/verify_release.py
```

La comprobacion local usa las copias TTS sin tokens y las ventanas declaradas. Recalcula 670 ensayos con 504 recepciones en las tres ventanas disponibles. La ventana 22:08-23:00 no tiene CSV ni recepciones: no se calcula PDR=0. La repeticion del 27 de octubre se incorpora como C27-0810; ver docs/RUTA4_27OCT.md.

## Entradas y codigo

- `src/matlab/MDPI_3DMSAGA_Trazable.m` y `config_campana_ambato.m`: auditoria congelada y escenario fisico separados.
- `src/matlab/datos/` y `fuentes/`: entradas verificables del segmento de 291 ensayos, con metadatos TTS sin campos secretos.
- `data/field_20261026/`: cronologia corregida y observaciones con y sin recepcion.
- `data/field_model_comparison/`: comparaciones previas y posteriores al ajuste; no reentrenadas con el recorrido.
- `data/single_gateway_legacy/`: evidencia de las cohortes anteriores.
- `data/geospatial/`: snapshot vial de referencia; sujeto a atribucion OSM.
- `provenance/redactions.json`: huellas original/preparada, serializacion y mapa de lineas. En ambas capturas se retiraron cero campos porque no habia secretos de transporte. No se modifican RSSI, tiempos, FCnt, SNR ni posiciones.

La etiqueta interna `R2_20261026_desde1400_aproximado` corresponde a C26-1400, es decir, Ruta 1 segun el horario del investigador; no se renombra retroactivamente una clave de ensayo.

En MATLAB, desde `src/matlab`, ejecutar `out=MDPI_3DMSAGA_Trazable;`. El modo por defecto reproduce la auditoria historica. El recuento tiene 291 ensayos, 267 recibidos y 103 candidatos de calle con RSSI asociado a 45 m. El recalculo fisico se detiene hasta documentar potencia, ganancias, alturas, perdidas y cotas compatibles. El rango de 2-3 dBi de antena FT es declarado, no una calibracion instrumental.

## Limites de interpretacion

Los contadores locales reinician entre pruebas; no identifican por si solos una sesion LoRaWAN. Las uniones preservadas usan secuencia, tiempo y receptor. La hora FT se interpreta como UTC-5 y no se corrige automaticamente la diferencia de unos9.3s. La posicion mas cercana a una interseccion es una asociacion provisional, no una precision GPS certificada.

La potencia exportada30dBm no se convierte sin comprobacion en potencia fisica. La ficha FT101 declara22dBm maximos a915MHz y la discrepancia se conserva. Tampoco se convierten pisos3/12 en metros ni se suman5dBi dos veces por haber dos antenas.

Las claves API nunca forman parte de esta entrega. Los originales privados se conservan bajo custodia del autor; la copia para difusion permite repetir la union de observaciones sin publicar tokens de transporte. La nueva repeticion C27-0810 esta verificada, con alcance espacial parcial por perdida de GNSS.

## Adquisición y fuentes originales

`data/field_20261026/ft_originals/` conserva los cuatro CSV recibidos byte a byte. El nombre del archivo de 50 pruebas no lo convierte en la Ruta 4 nocturna. `provenance/field_originals.json` identifica cada copia.

`scripts/extraer_tts_verificable.py` conserva la descarga directa desde Storage y su manifiesto. Puede auditarse sin conexión con `--input-jsonl`; la descarga con `--fetch` requiere una credencial privada suministrada por variable TTS_API_KEY o un archivo privado leído mediante AST, que no se ejecuta. No escribir la clave en comandos, capturas ni archivos del repositorio. El extractor no se ejecuta automáticamente al verificar la entrega.

`src/python_archived/` permite consultar el procesamiento usado en esta revisión. Conserva rutas del entorno de trabajo y depende de numpy/Pillow en algunos programas; su inclusión no declara portabilidad automática. Para recalcular las comprobaciones incluidas usar `scripts/verify_release.py`; para el contraste espacial congelado, el motor MATLAB documentado. La verificación vuelve a unir tiempos, contadores y posiciones con los CSV FT originales.

El script integrado original se conserva sanitizado en src/matlab_original_reference/; es una referencia historica con condiciones aun no armonizadas. El nombre Dataset_TTS_API_Validation no acredita por si solo una consulta a TTS. Su diferencia con la revision modular y las huellas de ambas fuentes se documentan en provenance. La cache altimetrica recibida se conserva en src/matlab/fuentes/; su nombre no certifica datum ni referencia vertical.

## Repetición Ruta 4 incorporada

432 ensayos, 332 con TTS, 181 con GPS y 35 candidatos de calle contrastados. RMSE calibrado congelado: 23,85 dB. No se oculta la discrepancia ni se reajusta con este recorrido. Ver [método, fuentes y límites](docs/RUTA4_27OCT.md).


## Sustento de la tesis

Ver [selección y procedimiento del capítulo 3](docs/SUSTENTO_CAPITULO3.md), [inventario MATLAB](docs/SELECCION_MATLAB_CAP3.csv) y [sección 3.7 editable](docs/SECCION_3_7_TESIS.tex).
