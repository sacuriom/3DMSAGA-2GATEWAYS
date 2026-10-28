"""Figura vectorial de Ruta 4 a partir de observaciones preservadas."""
from pathlib import Path
import argparse,csv
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data/field_20261027');p.add_argument('--output',type=Path,default=ROOT/'outputs/Ruta4_27oct_verificacion.pdf');args=p.parse_args()
A=args.data;F=ROOT;fig=args.output;fig.parent.mkdir(parents=True,exist_ok=True)
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
c=canvas.Canvas(str(fig),pagesize=(760,670));c.setTitle('Ruta 4 - 27 octubre 2026: registro radio y GNSS')
def text(x,y,s,size=10,col='#183247'):
    c.setFillColor(HexColor(col));c.setFont('Helvetica',size);c.drawString(x,y,s)
def line(x1,y1,x2,y2,col='#9ba8af',width=.6):c.setStrokeColor(HexColor(col));c.setLineWidth(width);c.line(x1,y1,x2,y2)
text(45,640,'Ruta 4 repetida: recepción conservada, localización incompleta',20)
rows=read(A/'resultados/ensayos_ventana_declarada.csv')
from datetime import datetime
start=datetime.fromisoformat('2026-10-27 08:10:00')
def tx(t):return 95+(datetime.fromisoformat(t)-start).total_seconds()/4560*605
for t,lab in [('08:10:00','08:10'),('08:30:00','08:30'),('08:50:00','08:50'),('09:10:00','09:10'),('09:26:00','09:26')]:
    x=tx('2026-10-27 '+t);line(x,479,x,590,'#dbe2e7');text(x-12,463,lab,14)
for key,y,label,color in [('gateway1_received',570,'Paltas','#2464a3'),('gateway2_received',535,'PUCESA','#1c805b'),('GPS_valid',500,'GPS','#7540a0')]:
    text(25,y-3,label,14)
    for r in rows:
        x=tx(r['Time_FT']);line(x,y-5,x,y+5,color if r[key]=='True' else '#e7eaed',1.1)
text(95,439,'432 ensayos; 332 con TTS; 181 con GPS. Sin posiciones interpoladas.',14)
text(95,421,'Señal FT ausente en 103 ensayos que sí tienen recepción TTS.',14)

assoc=read(A/'resultados/asociaciones_GPS.csv');nodes=read(F/'src/matlab/datos/nodos_referencia.csv')
x0,y0,w,h=75,92,300,275;xs=[float(r['Longitude']) for r in assoc];ys=[float(r['Latitude']) for r in assoc];xmin,xmax=min(xs)-.001,max(xs)+.001;ymin,ymax=min(ys)-.001,max(ys)+.001
def px(x):return x0+(x-xmin)/(xmax-xmin)*w
def py(y):return y0+(y-ymin)/(ymax-ymin)*h
text(60,386,'Posiciones GNSS disponibles, 08:10–08:41',15)
for n in nodes:
    x,y=float(n['Longitude']),float(n['Latitude'])
    if xmin<=x<=xmax and ymin<=y<=ymax:
        c.setFillColor(HexColor('#d9dee2'));c.circle(px(x),py(y),1,fill=1,stroke=0)
for r in assoc:
    c.setFillColor(HexColor('#2464a3' if r['TTS_received']=='True' else '#c34d45'));c.circle(px(float(r['Longitude'])),py(float(r['Latitude'])),2,fill=1,stroke=0)
for f in [0,.5,1]:
    x=xmin+(xmax-xmin)*f;y=ymin+(ymax-ymin)*f;line(px(x),y0,px(x),y0+h,'#e1e5e8');line(x0,py(y),x0+w,py(y),'#e1e5e8');text(px(x)-16,y0-14,f'{x:.3f}',14);text(x0-39,py(y)-3,f'{y:.3f}',14)
text(160,66,'Longitud (grados)',14)
c.saveState();c.translate(20,175);c.rotate(90);text(0,0,'Latitud (grados)',14);c.restoreState()
text(60,46,'Azul: TTS; rojo: sin recepción TTS; gris: candidatos.',14)
text(60,28,'Sin trayectoria reconstruida después de las 08:41:51.',14)

x0,y0,w,h=430,92,280,275;lo,hi=-145,-35
def fx(x):return x0+(x-lo)/(hi-lo)*w
def fy(y):return y0+(y-lo)/(hi-lo)*h
text(430,386,'Predicción congelada y RSSI observado',15)
for v in [-140,-120,-100,-80,-60,-40]:
    line(fx(v),y0,fx(v),y0+h,'#e1e5e8');line(x0,fy(v),x0+w,fy(v),'#e1e5e8');text(fx(v)-10,y0-14,str(v),14);text(x0-32,fy(v)-3,str(v),14)
line(fx(lo),fy(lo),fx(hi),fy(hi),'#80909b',1)
net=read(A/'resultados/network_cal_candidatos_45m.csv')
for r in net:
    c.setFillColor(HexColor('#c34d45' if r['Historical_RSSI']=='False' else '#2464a3'));c.circle(fx(float(r['Predicted_dBm'])),fy(float(r['Observed_median_dBm'])),3,fill=1,stroke=0)
c.saveState();c.translate(395,163);c.rotate(90);text(0,0,'Mediana observada (dBm)',14);c.restoreState()
text(465,58,'Predicción calibrada histórica (dBm)',14)
text(430,41,'35 candidatos; RMSE 23,85 dB; sin reajuste.',14)
text(430,25,'Mediana por candidato; radio de 45 m.',14)
c.save()
