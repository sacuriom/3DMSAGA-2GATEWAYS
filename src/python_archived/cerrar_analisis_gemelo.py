from pathlib import Path
import csv,json,math,hashlib,shutil,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'analisis_gemelo_20261026';F=O/'fuentes';F.mkdir(exist_ok=True)
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def f(x):return f'{float(x):.2f}'.replace('.',',')
S=json.loads((O/'resumen_exactitud.json').read_text(encoding='utf-8'))
nodes=read(O/'Dataset_TTS_API_Validation_original.csv');audit=read(O/'auditoria_intersecciones_114.csv');routes=read(O/'red_mejor_enlace_intersecciones_sin_anclas.csv')
M={x['series']:x for x in S['street_only_comparisons'] if x['radius_m']==45}
for src,dst in [
    (R/'validacion_ruta2_20261026/cruce_recorrido_desde14.csv',F/'cruce_recorrido_desde14.csv'),
    (R/'validacion_ruta2_20261026/26octRuta2Test.csv',F/'26octRuta2Test.csv'),
    (R/'validacion_ruta2_20261026/extraccion_tts/20261026T200441Z/respuesta_original.jsonl',F/'respuesta_original_TTS.jsonl'),
    (R/'analizar_exactitud_gemelo.py',O/'analizar_exactitud_gemelo.py')]:
    if src.exists():shutil.copy2(src,dst)
# Preserve method excerpts, excluding credential configuration lines.
mat=R/'evidencia_octubre/OCTUBRE/MDPI_3DMSAGA_Production_TTS_Integrated.m';lines=mat.read_text(encoding='utf-8-sig').splitlines()
extract=[]
for a,b in [(34,52),(76,100),(115,204),(289,324),(531,576),(612,628)]:
    extract.append(f'--- Líneas {a}–{b} ---')
    extract.extend(f'{i+1}: {lines[i]}' for i in range(a-1,min(b,len(lines))))
(F/'extractos_metodo_MATLAB.txt').write_text('\n'.join(extract),encoding='utf-8')
provenance={p.relative_to(O).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(F.iterdir()) if p.is_file()}
provenance['Dataset_TTS_API_Validation_original.csv']=dict(sha256=S['source_sha256'],bytes=(O/'Dataset_TTS_API_Validation_original.csv').stat().st_size)
provenance['MATLAB_original_sin_incluir_credenciales']=dict(source=str(mat),sha256=hashlib.sha256(mat.read_bytes()).hexdigest())
(O/'procedencia_sha256.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
fontpath='C:/Windows/Fonts/arial.ttf';boldpath='C:/Windows/Fonts/arialbd.ttf'
def font(n,b=False):return ImageFont.truetype(boldpath if b else fontpath,n)
# Scientific scatter panels: same calibrated axes, raw axes explicitly different.
im=Image.new('RGB',(1800,1460),'white');d=ImageDraw.Draw(im)
d.text((60,25),'Exactitud del gemelo: ajuste interno y contraste posterior',fill='#172e46',font=font(32,True))
old=[n for n in nodes if n['Measured_Field_RSSI_dBm'].lower() not in ('nan','','na')]
panels=[('A. Predicción original / 182 ubicaciones',[(max(float(n['RSSI_PUCESA_dBm']),float(n['RSSI_PALTAS_dBm'])),float(n['Measured_Field_RSSI_dBm'])) for n in old],(-180,10),S['internal_comparisons'][0],'Ajuste histórico; semántica RF del origen pendiente'),('B. Ajuste global / mismas 182 ubicaciones',[(float(n['Best_Predicted_RSSI_dBm']),float(n['Measured_Field_RSSI_dBm'])) for n in old],(-140,-20),S['internal_comparisons'][1],'Evaluación sobre los datos usados para calibrar'),('C. Ruta 2 / 103 intersecciones de calle',[(float(n['cal']),float(n['obs'])) for n in routes],(-140,-20),M['best_cal'],'Posterior, sin recalibrar; asociación provisional ≤45 m'),('D. Ruta 2 / 62 intersecciones sin RSSI histórico',[(float(n['cal']),float(n['obs'])) for n in routes if n['old']=='False'],(-140,-20),M['best_cal_new_locations'],'Subconjunto espacial nuevo; incertidumbre GPS pendiente')]
for k,(title,pts,lims,m,caption) in enumerate(panels):
    ox=40+(k%2)*890;oy=100+(k//2)*670;left=ox+92;top=oy+78;right=ox+800;bottom=oy+544;lo,hi=lims
    d.text((ox+10,oy),title,fill='#172e46',font=font(23,True));d.text((ox+10,oy+34),f"RMSE {f(m['rmse_dB'])} dB · MAE {f(m['mae_dB'])} dB · ±6 dB: {f(m['within_6dB_pct'])}%",fill='#394a57',font=font(20))
    def xx(x):return left+(x-lo)/(hi-lo)*(right-left)
    def yy(y):return bottom-(y-lo)/(hi-lo)*(bottom-top)
    for t in range(math.ceil(lo/20)*20,int(hi)+1,20):
        d.line((xx(t),top,xx(t),bottom),fill='#e2e8ef');d.line((left,yy(t),right,yy(t)),fill='#e2e8ef')
        d.text((xx(t)-20,bottom+9),str(t),fill='#364c60',font=font(17));d.text((left-53,yy(t)-10),str(t),fill='#364c60',font=font(17))
    d.line((left,bottom,right,top),fill='#555555',width=2)
    for x,y in pts:
        if lo<=x<=hi and lo<=y<=hi:d.ellipse((xx(x)-4,yy(y)-4,xx(x)+4,yy(y)+4),fill='#2176a7',outline='white',width=1)
    d.rectangle((left,top,right,bottom),outline='#6a7e8e',width=2)
    d.text((ox+245,bottom+40),'RSSI predicho (dBm)',fill='#172e46',font=font(21));d.text((ox+10,oy+632),caption,fill='#394a57',font=font(19))
    d.text((left,top+8),'Observado (dBm)',fill='#394a57',font=font(18))
d.text((60,1430),'Medianas por candidato en Ruta 2. Línea gris: igualdad. Los paneles A y B no son validación externa.',fill='#394a57',font=font(19))
im.save(O/'Exactitud_RSSI.png',dpi=(180,180))
# Geographical availability of measurements; no fabricated road geometry.
im=Image.new('RGB',(1500,1180),'white');d=ImageDraw.Draw(im);d.text((40,25),'Alcance espacial del contraste de campo',fill='#172e46',font=font(32,True))
xs=np.array([float(n['Longitude']) for n in nodes]);ys=np.array([float(n['Latitude']) for n in nodes]);cx=float(xs.mean());cy=float(ys.mean());scale=111.195
e=(xs-cx)*scale*math.cos(math.radians(cy));north=(ys-cy)*scale
emin,emax=e.min()-.12,e.max()+.12;nmin,nmax=north.min()-.12,north.max()+.12
ratio=min(1260/(emax-emin),880/(nmax-nmin));left=(1500-(emax-emin)*ratio)/2;top=100;right=left+(emax-emin)*ratio;bottom=top+(nmax-nmin)*ratio
def px(x):return left+(x-emin)*ratio
def py(y):return bottom-(y-nmin)*ratio
for t in range(math.ceil(emin),math.floor(emax)+1):d.line((px(t),top,px(t),bottom),fill='#e9edf2');d.text((px(t)-8,bottom+9),str(t),fill='#475a68',font=font(18))
for t in range(math.ceil(nmin),math.floor(nmax)+1):d.line((left,py(t),right,py(t)),fill='#e9edf2');d.text((left-35,py(t)-10),str(t),fill='#475a68',font=font(18))
historic={n['Node_ID'] for n in old};new={n['Node_ID'] for n in routes};colors={'none':'#ccd3db','old':'#d49c29','new':'#1976a8','both':'#813ea0'}
for category in ('none','old','new','both'):
    for j,n in enumerate(nodes):
        if j<2:continue
        a=n['Node_ID'] in historic;b=n['Node_ID'] in new;cat='both' if a and b else 'old' if a else 'new' if b else 'none'
        if cat!=category:continue
        rad=3 if cat=='none' else 5;xx=px(e[j]);yy=py(north[j]);d.ellipse((xx-rad,yy-rad,xx+rad,yy+rad),fill=colors[cat])
for j,label in [(0,'PUCESA'),(1,'Paltas')]:
    xx=px(e[j]);yy=py(north[j]);d.polygon([(xx,yy-11),(xx-9,yy+8),(xx+9,yy+8)],fill='#182d3e');d.text((xx+11,yy-13),label,fill='#182d3e',font=font(20,True))
d.rectangle((left,top,right,bottom),outline='#687b8d',width=2);d.text(((left+right)/2-75,bottom+25),'Este local (km)',fill='#172e46',font=font(22));d.text((left,top-28),'Norte local (km)',fill='#172e46',font=font(20))
legend=[('none','Sin RSSI histórico ni asociación nueva: 2.385'),('old','Solo RSSI histórico: 140'),('new','Solo Ruta 2: 62'),('both','Histórico y Ruta 2: 41')]
for i,(cat,label) in enumerate(legend):
    xx=60+(i%2)*720;yy=1055+(i//2)*42;d.ellipse((xx,yy+3,xx+14,yy+17),fill=colors[cat]);d.text((xx+24,yy),label,fill='#394a57',font=font(22))
d.text((60,1135),'2.628 candidatos de calle; anclas aparte. Azul/morado: asociación provisional ≤45 m; no certifica precisión GPS.',fill='#394a57',font=font(20))
im.save(O/'Alcance_espacial_intersecciones.png',dpi=(180,180))

def metricrow(label,m):return f"| {label} | {m['n']} | {f(m['rmse_dB'])} | {f(m['mae_dB'])} | {f(m['bias_obs_minus_pred_dB'])} | {f(m['within_6dB_pct'])}% | {f(m['within_10dB_pct'])}% |"
internal='\n'.join(metricrow(label,m) for label,m in zip(('Máximo original de los dos gateways','Máximo calibrado exportado'),S['internal_comparisons']))
external='\n'.join(metricrow(label,M[key]) for label,key in [('Gateway 1 / Paltas, original','gateway1'),('Gateway 2 / PUCESA, original','gateway2'),('Mejor enlace de red, original','best_raw'),('Mejor enlace de red, calibrado','best_cal'),('Calibrado: ubicaciones históricas repetidas','best_cal_old_locations'),('Calibrado: ubicaciones sin RSSI histórico','best_cal_new_locations')])
sensitivity=[]
for radius in (15,30,45,60):
    mm=next(x for x in S['street_only_comparisons'] if x['radius_m']==radius and x['series']=='best_cal')
    sensitivity.append(f"| {radius} m | {mm['n']} | {f(mm['rmse_dB'])} | {f(mm['mae_dB'])} | {f(mm['within_6dB_pct'])}% |")
example_rows=[]
for x in read(O/'ejemplos_intersecciones.csv'):
    if int(x['Node_ID'])<=2:continue
    if x['Node_ID'] not in ('1032','1753','795'):continue
    example_rows.append(f"| {x['Node_ID']} | {x['Primary_Street']} / {x['Intersecting_Street']} | {x['Gateway']} | {x['n_frames']} | {f(x['median_matching_distance_m'])} | {f(x['Predicted_raw_dBm'])} | {f(x['Median_observed_uplink_dBm'])} | {f(x['Residual_obs_minus_pred_dB'])} |")
report=f'''# Exactitud del gemelo digital y aporte de la Ruta 2

**Fecha de análisis:** 26 de octubre de 2026. **Objeto:** determinar qué evidencia aporta el dataset a la predicción de RSSI en candidatos de calle y qué valida el nuevo recorrido. Se conservan los archivos originales y no se recalibra el modelo con la Ruta 2.

## 1. Dictamen

El mecanismo de recolección permite contrastar recepción y señal por gateway con registros originales de TTS. La Ruta 2 aporta un contraste posterior útil del modelo congelado. Sin embargo, los resultados actuales **no justifican afirmar alta exactitud radioeléctrica en todas las intersecciones, cobertura urbana del 100 % ni superioridad experimental del despliegue 3D‑M‑SAGA**.

La columna calibrada del gemelo describe mejor el nivel general de señal que las columnas originales, pero conserva errores relevantes y mezcla una transformación global con predicciones por gateway sin ajustar. La evaluación histórica es interna. El contraste nuevo es provisional por incertidumbre en la asociación espacial y temporal y por diferencias en la configuración de potencia.

## 2. Qué contiene el dataset y qué representan sus cifras

Fuente entregada: `Results_Production_TTS_SF9_20261026_090112/Dataset_TTS_API_Validation.csv`. SHA‑256: `{S['source_sha256']}`.

- 2.630 filas, identificadores y coordenadas únicos: 2 anclas de infraestructura y 2.628 candidatos restantes.
- 182 filas tienen `Measured_Field_RSSI_dBm` finito: **6,92 % del total**. Son 181 candidatos de calle y una ancla. Los otros 2.448 registros no contienen un RSSI de campo numérico.
- 511 filas incluyen `Unnamed Road` en alguno de los nombres. Los nombres y coordenadas proceden del gemelo; no constituyen una comprobación topográfica de cada intersección.
- El código identifica intersecciones a partir de coordenadas OSM compartidas por nombres de calles distintos, redondeadas a cinco decimales. Esta regla puede omitir cruces sin nodo común o identificar coincidencias geométricas que requieren inspección. Los cruces a distinto nivel tampoco quedan certificados por esa regla.

El nombre «TTS API» del archivo no prueba su procedencia remota. La auditoría previa reconstruyó las 182 medias a partir del respaldo local, con diferencia máxima de 0,05 dB por redondeo. No hay que interpretar automáticamente esa columna como RSSI uplink por gateway. En cambio, el contraste nuevo utiliza `rx_metadata` de TTS y conserva la identidad del receptor. La documentación oficial describe RSSI en dBm y metadatos por antena receptora: [The Things Stack, Gateway Server APIs](https://www.thethingsindustries.com/docs/api/reference/grpc/gateway_server/) y [Data Formats](https://www.thethingsindustries.com/docs/the-things-stack/concepts/data-formats/).

## 3. Exactitud interna: ajuste y evaluación sobre los mismos 182 puntos

Se define residuo como **observado − predicho**. RMSE y MAE se expresan en dB. El porcentaje dentro de ±6 o ±10 dB indica tolerancia cumplida; no es una «exactitud porcentual» universal. No se calcula error porcentual sobre dBm.

| Predicción comparada | n | RMSE dB | MAE dB | Sesgo dB | Dentro ±6 dB | Dentro ±10 dB |
|---|---:|---:|---:|---:|---:|---:|
{internal}

La regresión reconstruida es aproximadamente:

`RSSI_cal = 0,20155 × max(RSSI_PUCESA_raw, RSSI_PALTAS_raw) − 60,47372`.

El script calcula `polyfit` y evalúa los residuos sobre los mismos 182 puntos. Por ello, la reducción de RMSE de 35,61 a 13,51 dB es **mejora del ajuste interno**, no validación independiente. El sesgo nulo está favorecido por el intercepto de la regresión. La correlación permanece aproximadamente en 0,350; el R² predictivo exportado es 0,123. Ninguno equivale a «12,3 % de exactitud» ni a «35 % de precisión».

El procedimiento histórico también usa `mean(sub.RSSI)` sin excluir explícitamente ausentes: la auditoría anterior identificó 65 ubicaciones con mezcla de lecturas válidas y ausentes cuya media termina como NaN. Corregirlo requerirá publicar una nueva versión de entrenamiento y conservar intacta la actual.

## 4. Contraste con el recorrido nuevo: alcance y procedimiento

Se utiliza la fase del CSV del FT101 desde las 14:00, conforme al inicio aproximado declarado del movimiento. El tramo anterior se trata como preparación estacionaria. El montaje exterior y la antena aproximadamente vertical están documentados por fotografías; estas no proporcionan por sí solas altura, ganancia ni calibración instrumental.

En la ventana móvil hay **291 ensayos**, de los cuales **267 tienen recepción almacenada en TTS (91,75 %)** y 24 no fueron encontrados en la extracción. Gateway 1 aparece en 167 y gateway 2 en 230; 130 fueron recibidos por ambos. Estos conteos validan recepción almacenada durante esa ventana, no cobertura de toda Ambato. No se deduce RSSI de un mensaje no recibido.

El cruce previo usa la correspondencia `FCnt = TxCnt + 1`, comprobada para esta sesión mediante secuencia, contenido y cronología; no se generaliza a otras sesiones. Se excluye el mensaje de reporte final. El registro original TTS preservado en este paquete contiene 741 mensajes en toda la sesión: 740 ensayos y ese reporte, no 741 ensayos móviles.

Para comparar el modelo se asigna cada coordenada FT al candidato más próximo mediante distancia horizontal local, sin moverla al eje de la calle y sin corregir automáticamente su reloj. Se ensayan radios de 15, 30, 45 y 60 m. Los identificadores son **gateway1 → Paltas** y **gateway2 → PUCESA**, diferentes del orden de las columnas/anclas de MATLAB.

Con 45 m:

- 268 de los 291 ensayos se asocian a candidatos; 246 de ellos tienen recepción en TTS.
- Hay 114 ubicaciones asociadas, de las cuales 105 tienen al menos una señal recibida. Nueve no tienen recepción observada en sus ensayos asociados; esto no prueba por sí solo ausencia permanente de cobertura.
- Dos de las 105 son anclas. El análisis principal de calles usa **103 intersecciones, el 3,92 % de los 2.628 candidatos de calle**: 41 ya tenían RSSI histórico y **62 no lo tenían**.
- Hay 150 parejas distintas candidato de calle–gateway con RSSI: 52 de Paltas y 98 de PUCESA. No son 150 posiciones independientes.
- La unión del RSSI histórico con las nuevas asociaciones alcanza **243 candidatos de calle de 2.628 (9,25 %)**. Es disponibilidad de contraste provisional, no porcentaje de puntos definitivamente validados.

Para evitar que las paradas con muchos mensajes dominen el resultado, se calcula una mediana por candidato y gateway. Para el mejor enlace de red, primero se toma el mayor RSSI **recibido** de cada ensayo y después su mediana por candidato. Solo se conoce la señal de receptores que reportaron el mensaje. El máximo observado está condicionado a la recepción y no sustituye la evaluación por gateway.

### Errores del recorrido posterior, sin recalibrar con estos datos

| Predicción comparada | n | RMSE dB | MAE dB | Sesgo dB | Dentro ±6 dB | Dentro ±10 dB |
|---|---:|---:|---:|---:|---:|---:|
{external}

Las columnas originales subestiman notablemente la señal recibida en esta comparación: sesgo de +20,16 dB en Paltas y +43,39 dB en PUCESA. Los R² predictivos originales son negativos; en esta muestra sus errores cuadráticos superan los de una referencia constante igual a la media observada. No basta una correlación positiva para afirmar exactitud de amplitud.

El máximo calibrado presenta **RMSE 11,76 dB, MAE 9,28 dB y 39,81 % dentro de ±6 dB** sobre las 103 intersecciones. El 90 % tiene error absoluto de hasta 20,26 dB y su R² predictivo es 0,283. En las 62 ubicaciones sin RSSI histórico, RMSE=10,82 dB y 41,94 % queda dentro de ±6 dB. Es evidencia inicial de transferencia a posiciones nuevas del corredor, sujeta a las limitaciones siguientes; no extrapola a toda la ciudad.

La comparación temporal no usa exactamente la misma variable histórica: antes se exportó una media local sin trazabilidad individual del receptor y ahora se usa mediana del mejor uplink identificado. Por ello no se debe presentar 13,51→11,76 dB como mejora experimental demostrada por las rutas.

### Sensibilidad al radio de asociación, sin anclas

| Radio máximo | Intersecciones con RSSI | RMSE calibrado dB | MAE calibrado dB | Dentro ±6 dB |
|---|---:|---:|---:|---:|
{chr(10).join(sensitivity)}

Estos valores no son un intervalo de confianza: cambia el conjunto de candidatos al cambiar el radio. La discrepancia no desaparece con un radio más estricto. A 15 m quedan solo 43 intersecciones; ni siquiera ese umbral certifica que la señal corresponda exactamente al cruce.

### Ejemplos auditables de discrepancias originales

Los nombres son los del dataset; la distancia es entre coordenada FT y candidato, no error GPS certificado. Los ejemplos tienen al menos dos recepciones y distancia mediana de asociación menor de 15 m. No representan una muestra aleatoria ni un límite de error.

| Nodo | Calles del dataset | Receptor | Mensajes | Distancia mediana m | Predicho dBm | Observado mediano dBm | Residuo dB |
|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(example_rows)}

## 5. Inconsistencias que afectan la interpretación de cobertura y MSAGA

1. **Mezcla de columnas antes y después del ajuste.** Las dos columnas de gateway se exportan sin calibrar; `Best_Predicted_RSSI_dBm` reemplaza el máximo original por la regresión global. No son tres resultados del mismo modelo de señal.
2. **Cobertura aparente inducida por la regresión.** El máximo original supera −131 dBm en 2.087/2.630 ubicaciones (79,35 %). El calibrado varía solo entre −91,7 y −60,4 dBm y supera ese umbral en 2.630/2.630. Ese 100 % es un resultado algebraico del ajuste exportado, no cobertura medida.
3. **Estados anteriores al ajuste.** `Validation_Status` se calcula antes de reemplazar la predicción. Sus conteos son 0:471, 1:1813, 2:131 y 3:215. El código solo marca coincidencia si ambos niveles superan el umbral; el resto no constituye una matriz completa de verdaderos/falsos positivos y negativos. Los ausentes históricos también entran en ese flujo. No debe obtenerse «exactitud de cobertura» dividiendo estados.
4. **Optimización y corrección desconectadas.** La matriz RF y la matriz binaria de cobertura se calculan antes del benchmark; la corrección global posterior del mejor enlace no recalcula esa matriz ni vuelve a optimizar. Mejorar el ajuste de una columna no demuestra que los sitios seleccionados por 3D‑M‑SAGA sean los mejores en campo.
5. **Validación de dos sitios y generalización a otros sitios.** Dos gateways fijos permiten estudiar sus enlaces y la diversidad de recepción. No validan experimentalmente todos los posibles enlaces de la matriz candidato–candidato ni una solución con gateways no desplegados. Deben separarse la verificación computacional del optimizador y la validación empírica del modelo de propagación.
6. **Trazabilidad de la tercera dimensión.** La caché de alturas se asigna por posición en un vector, sin comprobación visible por ID/coordenada en ese paso. Esto es un riesgo de correspondencia, no prueba de que las alturas estén mal. La altura efectiva está configurada como cero adicional y debe contrastarse con la altura real de instalación. Las clases de clutter y penalizaciones son reglas del modelo, no mediciones de obstáculos en cada enlace.

## 6. Qué falta para una validación defendible en las próximas rutas

**Resolver la asociación de señal a posición.** La diferencia FT−tiempo radio TTS tiene mediana próxima a 9,29 s. No se ha demostrado si corresponde a desfase de reloj o a la forma en que el FT fecha el ensayo. En movimiento puede asignar una señal al cruce equivocado; no procede desplazar el GPS sin identificar primero la semántica del tiempo. Registrar un hito temporal y un segmento estacionario identificable antes/después de cada ruta ayuda a investigarlo. Conservar posición GNSS y, si el equipo lo permite, calidad/fijación GNSS y una traza de posición independiente.

**Hacer comparable el enlace físico.** La campaña declara 30 dBm y el código usa 27 dBm, con una ganancia configurada de 5 dB. Documentar potencia efectiva del emisor, ganancias/pérdidas, frecuencia, SF, ancho de banda, altura y orientación del montaje, estado ADR y firmware. La diferencia nominal de potencia es 3 dB; no explica por sí sola sesgos de 20 y 43 dB. No se ha aplicado una corrección inventada de ganancia o potencia.

**Mantener una evaluación externa real.** Completar las cuatro rutas, repetirlas con configuración y montaje documentados y fijar antes del ajuste qué días/corredores quedan para calibración y cuáles para evaluación. Si se usan estos resultados para decidir o modificar el modelo, reservar una nueva repetición final sin tocar para estimar generalización. Las filas cercanas y los mensajes sucesivos no se deben repartir aleatoriamente como si fueran muestras espaciales independientes. La justificación de particiones espaciales/temporales se desarrolla en [Roberts et al., 2017](https://doi.org/10.1111/ecog.02881).

**Priorizar información nueva.** Las rutas deben aumentar candidatos y clases de entorno cubiertos, además del número de mensajes. Repetir mucho tiempo en Paltas añade estabilidad local pero poca cobertura espacial. Conservar el protocolo de conducción comparable; en una selección predefinida de cruces de cada entorno, obtener observaciones estacionarias repetidas cuando sea posible, registrando el punto real. No se exige detenerse exactamente en cada cruce ni se identifica cobertura de una calle completa a partir de un único mensaje.

**Separar resultados de señal y entrega.** Publicar por gateway RMSE, MAE, sesgo, percentiles, tolerancias predefinidas y residuos por entorno/distancia. Publicar por separado ensayos enviados, recepciones únicas, diversidad y mensajes no encontrados. Una ausencia de TTS no tiene RSSI numérico y no identifica automáticamente la causa de pérdida. No usar confirmaciones de downlink como si fueran entrega uplink.

**Unificar el modelo antes de optimizar.** Conservar `raw` y `calibrated`, versión/coeficientes y conjuntos de ajuste/evaluación. Si se calibra por enlace, propagar el modelo definido a la matriz de cobertura y repetir el benchmark computacional con esa misma versión. La calibración de dos gateways necesita verificar su transferencia antes de aplicarse a todos los sitios hipotéticos. Definir de antemano el umbral/tolerancia relevante para la tesis; ±6 y ±10 dB aquí son descriptores, no normas de aceptación. No se asignan intervalos de confianza de independencia a un único recorrido espacialmente correlacionado.

## 7. Redacción académica propuesta, limitada a lo comprobado

> El gemelo digital exportado incluyó 2.630 ubicaciones, correspondientes a dos anclas de infraestructura y 2.628 candidatos de calle. De ellas, 182 contaron con RSSI de campo numérico en el procesamiento histórico. El ajuste lineal global redujo el RMSE interno de 35,61 a 13,51 dB; dado que sus coeficientes se estimaron y evaluaron sobre las mismas observaciones, este resultado se interpreta como calibración interna. Un recorrido posterior, contrastado con metadatos originales de The Things Stack, permitió asociar provisionalmente señales uplink a 103 candidatos de calle dentro de un radio máximo de 45 m. Sin recalibrar la versión exportada, el RMSE del mejor enlace calibrado fue de 11,76 dB, con MAE de 9,28 dB y 39,81 % de candidatos dentro de ±6 dB. De estos candidatos, 62 carecían de RSSI histórico y presentaron RMSE de 10,82 dB. La evidencia muestra capacidad inicial de contraste externo en el corredor observado, pero no permite certificar alta exactitud en toda la red de intersecciones ni validar experimentalmente la optimalidad del despliegue 3D‑M‑SAGA. La interpretación está condicionada por la sincronización temporal, la incertidumbre de posición, la comparabilidad de la configuración radio y la necesidad de repetir recorridos reservados para evaluación.

## 8. Archivos y reproducibilidad

- `auditoria_intersecciones_114.csv`: tabla de cada ubicación visitada, calles, tipo de punto, número de ensayos/recepciones, distancias de asociación, RSSI predicho/observado por gateway y errores. Incluye nueve ubicaciones sin RSSI recibido y dos anclas identificadas.
- `exactitud_interna_182.csv`, `exactitud_sin_anclas.csv`: todas las métricas, radios y subconjuntos de la evaluación principal.
- `pares_provisionales_por_gateway.csv`: cada recepción identificada, sus coordenadas, candidato más próximo y residuo; incluye distancias mayores de 45 m para auditoría, que no entran en la tabla principal.
- `correspondencias_291_pruebas.csv`: también conserva los ensayos sin recepción y el candidato más próximo.
- `medianas_por_interseccion_gateway_45m.csv` y `red_mejor_enlace_intersecciones_sin_anclas.csv`: agregados que permiten reconstruir los errores. La primera conserva las anclas y debe filtrarse por ID>2 para reproducir la tabla de calles.
- `Exactitud_RSSI.png` y `Alcance_espacial_intersecciones.png`: figuras calculadas con estos datos, sin geolocalización o valores inventados.
- `fuentes/`: CSV del FT, cruce móvil anterior, JSONL original TTS y extractos numerados del método MATLAB sin credenciales. `procedencia_sha256.json` documenta las huellas.
- `analizar_exactitud_gemelo.py`: análisis reproducible con Python y NumPy, usando los CSV preservados cuando la ubicación original no existe. No consulta TTS ni modifica el modelo. Para reproducir la extracción y el cruce completos, conservar también el paquete anterior `Validacion_Ruta2_26oct2026.zip` y su informe de sesión.

No se ha modificado la tesis ni los datos originales. No se han simulado lecturas faltantes ni certificado alturas, precisión GPS, calibración instrumental o cobertura fuera del recorrido.
'''
(O/'INFORME_EXACTITUD_GEMELO.md').write_text(report,encoding='utf-8')
# Include only this task's explicit deliverables and preserved data.
archive=R/'Analisis_exactitud_Gemelo_Ruta2_26oct2026.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(O.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(R))
print(json.dumps(dict(report=str(O/'INFORME_EXACTITUD_GEMELO.md'),zip=str(archive),zip_bytes=archive.stat().st_size,preserved_files=list(provenance)),ensure_ascii=False,indent=2))
