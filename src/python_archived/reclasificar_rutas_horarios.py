from pathlib import Path
import json,csv,math,statistics,hashlib,shutil,zipfile
from datetime import datetime,timedelta,timezone
from collections import Counter
from PIL import Image,ImageDraw,ImageFont
from auditar_cuatro_rutas import OUT,ROOT,read,write,dist

WINDOWS=[('Ruta 1','Ruta2','14:00:00','15:10:00'),('Ruta 2','Ruta1','16:20:00','17:00:00'),('Ruta 3','Ruta3','21:38:00','22:04:00'),('Ruta 4',None,'22:08:00','23:00:00')]
source_names={'Ruta1':'26octRuta1.csv','Ruta2':'26octRuta2Test (1).csv','Ruta3':'26octTuta3.csv','Ruta4':'26octRura4(amla).csv'}
specs=[];selected={};outliers=[];allrows=[]
for declared,filelabel,start,end in WINDOWS:
    st='2026-10-26 '+start;en='2026-10-26 '+end
    rows=read(OUT/(filelabel+'_cruce_TTS.csv')) if filelabel else []
    ss=[dict(r,Declared_Route=declared,Source_File=source_names[filelabel]) for r in rows if st<=r['Time_FT']<=en]
    selected[declared]=ss;allrows+=ss
    row=dict(Declared_Route=declared,Declared_start=st,Declared_end=en,Declared_minutes=(datetime.fromisoformat(en)-datetime.fromisoformat(st)).total_seconds()/60,Source_File=source_names[filelabel] if filelabel else 'No hay CSV correspondiente',Rows=len(ss),Recorded_first=ss[0]['Time_FT'] if ss else None,Recorded_last=ss[-1]['Time_FT'] if ss else None)
    if ss:
        dt=[(datetime.fromisoformat(b['Time_FT'])-datetime.fromisoformat(a['Time_FT'])).total_seconds() for a,b in zip(ss,ss[1:])]
        pts=[(float(r['Latitude']),float(r['Longitude'])) for r in ss];gps=[all(math.isfinite(x) for x in p) for p in pts];steps=[dist(a,b) for a,b in zip(pts,pts[1:])]
        finite=sum(math.isfinite(float(r['FT_RSSI_dBm'])) for r in ss);heard=sum(r['TTS_received']=='True' for r in ss)
        row.update(Recorded_span_min=(datetime.fromisoformat(ss[-1]['Time_FT'])-datetime.fromisoformat(ss[0]['Time_FT'])).total_seconds()/60,Tx_first=int(ss[0]['Tx_Cnt']),Tx_last=int(ss[-1]['Tx_Cnt']),Counter_gaps=sum(int(b['Tx_Cnt'])-int(a['Tx_Cnt'])!=1 for a,b in zip(ss,ss[1:])),Median_interval_s=statistics.median(dt),Max_interval_s=max(dt),GPS_rows=sum(gps),FT_RSSI_rows=finite,FT_RSSI_pct=finite/len(ss)*100,TTS_received=heard,TTS_not_found=len(ss)-heard,Stored_reception_pct=heard/len(ss)*100,GW1=sum(r['GW1_received']=='True' for r in ss),GW2=sum(r['GW2_received']=='True' for r in ss),Both=sum(r['N_gateways']=='2' for r in ss),GPS_polyline_km=sum(x for x in steps if math.isfinite(x))/1000,Steps_over80kmh=sum(math.isfinite(s) and t>0 and s/t*3.6>80 for s,t in zip(steps,dt)),Late_unrecorded_tail_min=max(0,(datetime.fromisoformat(en)-datetime.fromisoformat(ss[-1]['Time_FT'])).total_seconds()/60))
        for i in range(1,len(pts)-1):
            a=dist(pts[i-1],pts[i]);b=dist(pts[i],pts[i+1]);c=dist(pts[i-1],pts[i+1])
            if math.isfinite(a+b+c) and a>100 and b>100 and c<60:outliers.append(dict(Declared_Route=declared,Time_FT=ss[i]['Time_FT'],Tx_Cnt=ss[i]['Tx_Cnt'],Previous_to_point_m=a,Point_to_next_m=b,Previous_to_next_m=c,Issue='Posible excursion GNSS aislada; no eliminada'))
    specs.append(row)
write('resumen_rutas_por_horario.csv',specs);write('ensayos_ventanas_declaradas.csv',allrows);write('posibles_excursiones_GNSS.csv',outliers)
# Inspect all received messages, including the ones not linked to a CSV.
events=[]
path=OUT/'extraccion_tts/20261027T041849Z/respuesta_original.jsonl'
for line in path.read_text(encoding='utf-8-sig').splitlines():
    if not line.strip():continue
    if line.startswith('data:'):line=line[5:]
    d=json.loads(line)['result'];u=d['uplink_message'];time=u['settings'].get('time',d['received_at']);local=datetime.fromisoformat(time.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=-5)))
    events.append(dict(FCnt=u['f_cnt'],Time_TTS_UTC=time,Time_Ecuador=local.isoformat(),Device_ID=d['end_device_ids'].get('device_id'),DevAddr=d['end_device_ids'].get('dev_addr'),Payload_base64=u.get('frm_payload','')))
begin=datetime.fromisoformat('2026-10-26T22:08:00-05:00');finish=datetime.fromisoformat('2026-10-26T23:00:00-05:00')
during=[r for r in events if begin<=datetime.fromisoformat(r['Time_Ecuador'])<=finish];before=[r for r in events if datetime.fromisoformat(r['Time_Ecuador'])<begin][-1];after=[r for r in events if datetime.fromisoformat(r['Time_Ecuador'])>finish][0]
write('limites_TTS_ruta4_real.csv',[dict(Relation='last_before',**before),*[dict(Relation='during',**r) for r in during],dict(Relation='first_after',**after)])
matches=read(OUT/'asociaciones_provisionales_intersecciones.csv');union=set()
for spec,(_,filelabel,_,_) in zip(specs,WINDOWS):
    ss=selected[spec['Declared_Route']];txs={int(r['Tx_Cnt']) for r in ss}
    eligible=[m for m in matches if m['Route']==filelabel and int(m['Tx_Cnt']) in txs and m['Within45m']=='True' and m['Infrastructure']=='False']
    visited={int(m['Node_ID']) for m in eligible};heard={int(m['Node_ID']) for m in eligible if m['TTS_received']=='True'};union|=heard
    spec.update(Street_candidates_visited_45m=len(visited),Street_candidates_with_TTS_RSSI_45m=len(heard),GPS_points_outside_2800m_ROI=sum(math.isfinite(float(r['Latitude'])) and math.isfinite(float(r['Longitude'])) and dist((-1.26309,-78.63346),(float(r['Latitude']),float(r['Longitude'])))>2800 for r in ss))
write('resumen_rutas_por_horario.csv',specs)
result=dict(Routes=specs,ActualRoute4=dict(ReceivedMessagesInDeclaredWindow=len(during),Before=before,After=after,Comment='Sin CSV ni denominador Tx para esa ventana; no calcular PDR=0'),GPS_Excursions=outliers)
result['UniqueStreetCandidatesWithRSSI_declaredWindows']=len(union)
(OUT/'reclasificacion_horarios.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))

# Map the declared windows. The fourth route has no measured geometry.
nodes=read(ROOT/'analisis_gemelo_20261026/Dataset_TTS_API_Validation_original.csv');colors={'Ruta 1':'#23915a','Ruta 2':'#1675b4','Ruta 3':'#d78319'}
im=Image.new('RGB',(1400,1100),'white');d=ImageDraw.Draw(im)
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if b else 'C:/Windows/Fonts/arial.ttf',n)
d.text((40,25),'Rutas identificadas por los horarios declarados',font=font(30,True),fill='#142e42')
west,south,east,north=-78.651,-1.278,-78.602,-1.225;left,top,right,bottom=100,115,960,955;scale=min((right-left)/((east-west)*math.cos(math.radians(-1.25))),(bottom-top)/(north-south));right=left+(east-west)*math.cos(math.radians(-1.25))*scale;bottom=top+(north-south)*scale
def pixel(lat,lon):return left+(lon-west)*math.cos(math.radians(-1.25))*scale,bottom-(lat-south)*scale
for n in nodes:
    lat=float(n['Latitude']);lon=float(n['Longitude'])
    if west<=lon<=east and south<=lat<=north:
        x,y=pixel(lat,lon);d.ellipse((x-2,y-2,x+2,y+2),fill='#dce1e6')
for label,color in colors.items():
    previous=None
    for r in selected[label]:
        lat=float(r['Latitude']);lon=float(r['Longitude'])
        if not(math.isfinite(lat) and math.isfinite(lon)):previous=None;continue
        point=pixel(lat,lon)
        if previous:d.line((*previous,*point),fill=color,width=3)
        x,y=point;d.ellipse((x-3,y-3,x+3,y+3),fill=color);previous=point
for lat,lon,name in [(-1.2516,-78.62772,'Paltas'),(-1.27458,-78.6392,'PUCESA')]:
    x,y=pixel(lat,lon);d.polygon([(x,y-9),(x-8,y+7),(x+8,y+7)],fill='#142e42');d.text((x+12,y-12),name,font=font(20,True),fill='#142e42')
d.rectangle((left,top,right,bottom),outline='#8b99a7',width=2)
for i,(label,color) in enumerate(colors.items()):
    y=220+i*70;d.line((950,y+10,990,y+10),fill=color,width=5);d.text((1005,y),label,font=font(25,True),fill='#142e42')
d.text((950,480),'Ruta 4: 22:08–23:00',font=font(23,True),fill='#a02e3d');d.text((950,520),'Sin CSV correspondiente',font=font(20),fill='#a02e3d');d.text((950,554),'Sin mensajes en TTS',font=font(20),fill='#a02e3d')
d.text((950,670),'El archivo de 50 filas',font=font(20),fill='#425766');d.text((950,701),'es de 17:05–17:14;',font=font(20),fill='#425766');d.text((950,732),'no representa Ruta 4.',font=font(20),fill='#425766')
d.text((45,1005),'Ventanas recortadas según el investigador. Puntos grises: candidatos del gemelo.',font=font(22),fill='#425766');d.text((45,1040),'Se conservan las coordenadas originales; sin certificar precisión GNSS ni desplazar tiempos.',font=font(21),fill='#425766')
im.save(OUT/'Mapa_rutas_por_horario.png',dpi=(170,170))
