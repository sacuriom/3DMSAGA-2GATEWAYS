# Diccionario de archivos principales

Los nombres de columna se conservan tal como fueron exportados. RSSI se expresa en dBm y SNR en dB; porcentajes y proporciones se distinguen por el encabezado. Un campo vacío no equivale a cero.


## data/field_20261026/ensayos_ventanas_declaradas.csv

Filas de datos: 670.


`Route`, `Row`, `Time_FT`, `Tx_Cnt`, `Expected_FCnt`, `FCnt_offset`, `Latitude`, `Longitude`, `FT_RSSI_dBm`, `TTS_received`, `N_gateways`, `GW1_received`, `GW2_received`, `Time_TTS_radio`, `FT_minus_radio_s`, `TTS_source`, `TTS_source_line`, `gateway1_RSSI_dBm`, `gateway2_RSSI_dBm`, `Declared_Route`, `Source_File`.


## data/field_20261026/resumen_rutas_por_horario.csv

Filas de datos: 4.


`Declared_Route`, `Declared_start`, `Declared_end`, `Declared_minutes`, `Source_File`, `Rows`, `Recorded_first`, `Recorded_last`, `Recorded_span_min`, `Tx_first`, `Tx_last`, `Counter_gaps`, `Median_interval_s`, `Max_interval_s`, `GPS_rows`, `FT_RSSI_rows`, `FT_RSSI_pct`, `TTS_received`, `TTS_not_found`, `Stored_reception_pct`, `GW1`, `GW2`, `Both`, `GPS_polyline_km`, `Steps_over80kmh`, `Late_unrecorded_tail_min`, `Street_candidates_visited_45m`, `Street_candidates_with_TTS_RSSI_45m`, `GPS_points_outside_2800m_ROI`.


## data/field_model_comparison/red_mejor_enlace_intersecciones_sin_anclas.csv

Filas de datos: 103.


`Node_ID`, `raw`, `cal`, `obs`, `old`.


## src/matlab/datos/ensayos.csv

Filas de datos: 291.


`TrialKey`, `Tx_Cnt`, `Expected_FCnt`, `Time_FT_original`, `Latitude`, `Longitude`, `Latitude_original`, `Longitude_original`, `SF`, `FT_Power_dBm`, `TTS_received`, `Time_TTS_radio`, `FTMinusRadio_s`, `FrameKey`, `Position_source`, `Time_position_semantics`, `Campaign_ID`.


## src/matlab/datos/recepciones.csv

Filas de datos: 397.


`TrialKey`, `FrameKey`, `Tx_Cnt`, `FCnt`, `Device_ID`, `DevAddr`, `Session_key_id`, `Gateway_ID`, `Antenna_index`, `RSSI_dBm`, `SNR_dB`, `Signal_RSSI_dBm`, `Frequency_Hz`, `SF`, `Bandwidth_Hz`, `Coding_rate`, `Time_TTS_radio`, `Time_TTS_gateway`, `Time_TTS_server`, `FTMinusRadio_s`, `FT_Power_dBm`, `Latitude`, `Longitude`, `TTS_original_line`.


## src/matlab/datos/nodos_referencia.csv

Filas de datos: 2630.


`Node_ID`, `Primary_Street`, `Intersecting_Street`, `Latitude`, `Longitude`, `Elevation_MSNM`, `Clutter_Class`, `RSSI_PUCESA_dBm`, `RSSI_PALTAS_dBm`, `Best_Predicted_RSSI_dBm`, `Measured_Field_RSSI_dBm`, `Validation_Status`.
