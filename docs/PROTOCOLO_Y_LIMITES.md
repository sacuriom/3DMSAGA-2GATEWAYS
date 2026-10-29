# Identidad de campañas y límites de inferencia

Los nombres de archivo no identifican la ruta. Ventanas declaradas, hora local Ecuador UTC−5: C26-1400/Ruta 1, 14:00–15:10; C26-1620/Ruta 2, 16:20–17:00; C26-2138/Ruta 3, 21:38–22:04; C26-2208/Ruta 4, 22:08–23:00.

Ruta 1: 291 ensayos disponibles hasta 14:51:45 y 267 recibidos. No cubre los últimos 18 min 15 s de la ventana declarada. Ruta 2: 231/134. Ruta 3: 148/103, con cinco posiciones no válidas y dos excursiones GNSS marcadas. Ruta 4 original: sin CSV ni denominador; cero recepciones observadas no significa PDR=0. El ensayo de 50 mensajes de las 17:05 no se atribuye a esa ruta. La repetición del 27 de octubre se incorpora por separado como C27-0810; no se imputa a la ventana original.

R2_20261026_desde1400_aproximado es una etiqueta interna heredada del segmento C26-1400; no significa la Ruta 2 declarada posteriormente. gateway1 identifica Paltas y ocupa la segunda posición del arreglo MATLAB; gateway2 identifica PUCESA y ocupa la primera. Se conservan identificadores en vez de unir por posición de fila.

Los objetos JSON de las dos capturas TTS son iguales a los originales recibidos; las copias preparadas cambian serialización y eliminan líneas vacías. No se encontraron ni retiraron campos sensibles. `provenance/redactions.json` conserva ambas huellas y la correspondencia de líneas físicas; `TTS_original_line` sigue refiriéndose al original y `TTS_prepared_line` a la copia compacta.

El contraste usa predicciones congeladas, radio principal 45 m y medianas por candidato/receptor; excluye dos anclas de infraestructura. No ajusta otra vez con el recorrido. Los 103 candidatos producen RMSE 11,7647 dB en el máximo de red calibrado históricamente; no constituyen una calibración por gateway ni certifican el resto de intersecciones. El ajuste interno histórico de 182 puntos y el contraste posterior de 103 tienen poblaciones y agregaciones distintas: no se interpreta su diferencia como mejora del modelo.

La hora del FT y la hora radio TTS difieren unos 9,3 s con semántica pendiente; no se desplaza automáticamente el GPS. Una asociación a 45 m no acredita una precisión de posición de 45 m. No se crean RSSI para mensajes ausentes, no se cambia ausencia por −150 dBm y no se confunden mensajes únicos con copias recibidas por varios gateways.

Montaje: FT en parrilla, unos 1,80 m sobre suelo, declarado por el investigador; antena FT típica 2–3 dBi declarada. Paltas, tercer piso; PUCESA, duodécimo, sin conversión supuesta a metros. Solo una etiqueta fotografiada acredita 5 dBi nominales; falta confirmar su aplicación a las cuatro antenas. ASL y AGL se mantienen separados. TX30 dBm en la exportación no se certifica como potencia física: la ficha FT101 declara 22 dBm máximos en 915 MHz. Esta discrepancia impide atribuir toda diferencia de señal al predictor.

La cohorte de 2153 puntos de simulación no se sustituye por los 2630 registros del dataset de campo (2628 candidatos de calle y dos anclas). Se documentan 87 posiciones fuera del ROI en C26-1620 y 11 en C26-2138; no se fuerzan a candidatos del borde.

La repetición C27-0810 aporta 432 ensayos, 332 recepciones y solo 181 posiciones. El contraste congelado de 35 candidatos tiene RMSE 23,85 dB y no reproduce la concordancia del segmento anterior. Véase RUTA4_27OCT.md.
