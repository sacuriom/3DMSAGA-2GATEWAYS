from pathlib import Path
import csv,json,math,hashlib,shutil,collections
import numpy as np
R=Path(__file__).resolve().parent
if R.name=='analisis_gemelo_20261026':R=R.parent
O=R/'analisis_gemelo_20261026';O.mkdir(exist_ok=True)
source=Path('D:/DOCTORADOUPS/TESIS/OCTUBRE/Results_Production_TTS_SF9_20261026_090112/Dataset_TTS_API_Validation.csv')
if not source.exists():source=O/'Dataset_TTS_API_Validation_original.csv'
if source.resolve()!=(O/'Dataset_TTS_API_Validation_original.csv').resolve():shutil.copy2(source,O/'Dataset_TTS_API_Validation_original.csv')
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def num(x):
    try:return float(x)
    except (ValueError,TypeError):return math.nan
def write(name,rows):
    if not rows:return
    with (O/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def metrics(pred,obs):
    x=np.array(pred,float);y=np.array(obs,float);v=np.isfinite(x)&np.isfinite(y);x=x[v];y=y[v];e=y-x
    if not len(e):return dict(n=0)
    out=dict(n=len(e),rmse_dB=float(np.sqrt(np.mean(e**2))),mae_dB=float(np.mean(abs(e))),bias_obs_minus_pred_dB=float(e.mean()),median_abs_error_dB=float(np.median(abs(e))),p90_abs_error_dB=float(np.percentile(abs(e),90)),pearson_r=float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else None,predictive_R2=float(1-np.sum(e**2)/np.sum((y-y.mean())**2)))
    for margin in (3,6,10,15):out[f'within_{margin}dB_n']=int((abs(e)<=margin).sum());out[f'within_{margin}dB_pct']=float((abs(e)<=margin).mean()*100)
    return out
nodes=read(source);N=len(nodes);puc=np.array([num(r['RSSI_PUCESA_dBm']) for r in nodes]);pal=np.array([num(r['RSSI_PALTAS_dBm']) for r in nodes]);raw=np.maximum(puc,pal);cal=np.array([num(r['Best_Predicted_RSSI_dBm']) for r in nodes]);obs=np.array([num(r['Measured_Field_RSSI_dBm']) for r in nodes]);v=np.isfinite(obs)
fit=np.polyfit(raw[v],obs[v],1);allfit=np.polyfit(raw,cal,1)
internal=[]
for label,x in [('Raw max of two gateways',raw),('Exported calibrated maximum',cal)]:internal.append(dict(comparison=label,**metrics(x,obs)))
write('exactitud_interna_182.csv',internal)
status=collections.Counter(r['Validation_Status'] for r in nodes)
summary=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),nodes=N,unique_ids=len(set(r['Node_ID'] for r in nodes)),unique_coordinates=len(set((r['Latitude'],r['Longitude']) for r in nodes)),anchors=2,finite_measurement_nodes=int(v.sum()),measurement_fraction_pct=float(v.mean()*100),internal_comparisons=internal,training_linear_fit=dict(slope=float(fit[0]),intercept=float(fit[1])),exported_calibration_reconstruction=dict(slope=float(allfit[0]),intercept=float(allfit[1]),max_abs_residual_dB=float(np.max(abs(cal-np.polyval(allfit,raw))))),raw_range_dBm=[float(raw.min()),float(raw.max())],calibrated_range_dBm=[float(cal.min()),float(cal.max())],raw_covered_at_minus131=int((raw>=-131).sum()),calibrated_covered_at_minus131=int((cal>=-131).sum()),status_counts=dict(status),second_street_crossroad_count=sum(r['Intersecting_Street']=='Crossroad' for r in nodes),unnamed_in_either_street_count=sum('Unnamed Road' in (r['Primary_Street'],r['Intersecting_Street']) for r in nodes))

route_source=R/'validacion_ruta2_20261026/cruce_recorrido_desde14.csv'
if not route_source.exists():route_source=O/'fuentes/cruce_recorrido_desde14.csv'
ft=read(route_source)
def xy(lat,lon):return np.array([(lon+78.63346)*math.pi/180*6371000*math.cos(math.radians(-1.26309)),(lat+1.26309)*math.pi/180*6371000])
pos=np.array([xy(num(r['Latitude']),num(r['Longitude'])) for r in nodes]);pairs=[];gpsmatch=[];network=[]
for f in ft:
    q=xy(num(f['Latitude']),num(f['Longitude']));ds=np.linalg.norm(pos-q,axis=1);j=int(ds.argmin());n=nodes[j]
    gpsmatch.append(dict(Tx_Cnt=int(f['Tx_Cnt']),Node_ID=n['Node_ID'],Distance_m=float(ds[j]),TTS_received=f['TTS_received']=='True'))
    heard=[]
    for gw,key in [('gateway1','RSSI_PALTAS_dBm'),('gateway2','RSSI_PUCESA_dBm')]:
        value=num(f[gw+'_RSSI_dBm'])
        if not math.isfinite(value):continue
        heard.append(value)
        pairs.append(dict(Tx_Cnt=int(f['Tx_Cnt']),Node_ID=n['Node_ID'],Primary_Street=n['Primary_Street'],Intersecting_Street=n['Intersecting_Street'],Clutter=n['Clutter_Class'],Latitude=num(f['Latitude']),Longitude=num(f['Longitude']),Node_Latitude=num(n['Latitude']),Node_Longitude=num(n['Longitude']),Match_distance_m=float(ds[j]),Gateway=gw,Predicted_raw_dBm=num(n[key]),Measured_uplink_dBm=value,Residual_obs_minus_pred_dB=value-num(n[key]),Time_FT=f['Time_FT_original'],Time_TTS_radio=f['TTS_radio_time']))
    if heard:network.append(dict(Node_ID=n['Node_ID'],Match_distance_m=float(ds[j]),Raw_best_pred_dBm=float(raw[j]),Calibrated_best_pred_dBm=float(cal[j]),Best_received_RSSI_dBm=max(heard),Node_in_historical_calibration=bool(v[j])))
write('correspondencias_291_pruebas.csv',gpsmatch);write('pares_provisionales_por_gateway.csv',pairs)
audit=[];ft_by_tx={int(f['Tx_Cnt']):f for f in ft}
for nid in sorted(set(p['Node_ID'] for p in gpsmatch if p['Distance_m']<=45),key=int):
    matched=[p for p in gpsmatch if p['Distance_m']<=45 and p['Node_ID']==nid];node=nodes[int(nid)-1];frames=[ft_by_tx[p['Tx_Cnt']] for p in matched];j=int(nid)-1
    rec=sum(f['TTS_received']=='True' for f in frames);rr=dict(Node_ID=nid,Point_type='gateway_anchor' if int(nid)<=2 else 'street_candidate',Primary_Street=node['Primary_Street'],Intersecting_Street=node['Intersecting_Street'],Latitude=node['Latitude'],Longitude=node['Longitude'],Historical_RSSI_available=bool(v[j]),N_tests=len(frames),N_received_TTS=rec,N_not_found_TTS=len(frames)-rec,Stored_reception_pct=100*rec/len(frames),Match_min_m=min(p['Distance_m'] for p in matched),Match_median_m=float(np.median([p['Distance_m'] for p in matched])),Match_max_m=max(p['Distance_m'] for p in matched),Raw_best_pred_dBm=float(raw[j]),Calibrated_best_pred_dBm=float(cal[j]))
    best=[]
    for f in frames:
        values=[num(f[g+'_RSSI_dBm']) for g in ('gateway1','gateway2')];values=[x for x in values if math.isfinite(x)]
        if values:best.append(max(values))
    rr.update(Median_best_received_dBm=float(np.median(best)) if best else None,Error_cal_obs_minus_pred_dB=float(np.median(best))-float(cal[j]) if best else None)
    for gw,key in [('gateway1','RSSI_PALTAS_dBm'),('gateway2','RSSI_PUCESA_dBm')]:
        values=[num(f[gw+'_RSSI_dBm']) for f in frames];values=[x for x in values if math.isfinite(x)];pred=num(node[key]);med=float(np.median(values)) if values else None
        rr.update({gw+'_N_received':len(values),gw+'_Raw_pred_dBm':pred,gw+'_Observed_median_dBm':med,gw+'_Error_obs_minus_pred_dB':med-pred if med is not None else None})
    audit.append(rr)
write('auditoria_intersecciones_114.csv',audit)
route_metrics=[];aggregated=[]
for radius in (15,30,45,60):
    for gw in ('gateway1','gateway2'):
        ss=[p for p in pairs if p['Match_distance_m']<=radius and p['Gateway']==gw];groups=collections.defaultdict(list)
        for p in ss:groups[p['Node_ID']].append(p)
        aa=[dict(Node_ID=k,Gateway=gw,Primary_Street=vv[0]['Primary_Street'],Intersecting_Street=vv[0]['Intersecting_Street'],Clutter=vv[0]['Clutter'],n_frames=len(vv),Predicted_raw_dBm=vv[0]['Predicted_raw_dBm'],Median_observed_uplink_dBm=float(np.median([x['Measured_uplink_dBm'] for x in vv])),median_matching_distance_m=float(np.median([x['Match_distance_m'] for x in vv]))) for k,vv in groups.items()]
        route_metrics.append(dict(radius_m=radius,Gateway=gw,unit='candidate_gateway_pair_median',matched_frame_receptions=len(ss),**metrics([x['Predicted_raw_dBm'] for x in aa],[x['Median_observed_uplink_dBm'] for x in aa])))
        if radius==45:aggregated.extend(aa)
    ss=[p for p in network if p['Match_distance_m']<=radius];groups=collections.defaultdict(list)
    for p in ss:groups[p['Node_ID']].append(p)
    aa=[dict(Node_ID=k,raw=vv[0]['Raw_best_pred_dBm'],cal=vv[0]['Calibrated_best_pred_dBm'],obs=float(np.median([x['Best_received_RSSI_dBm'] for x in vv])),old=vv[0]['Node_in_historical_calibration']) for k,vv in groups.items()]
    for label in ('raw','cal'):
        route_metrics.append(dict(radius_m=radius,Gateway='network_best_'+label,unit='candidate_median_of_best_received',matched_frame_receptions=len(ss),**metrics([x[label] for x in aa],[x['obs'] for x in aa])))
    if radius==45:
        summary['route45_summary']=dict(all_test_rows=len(ft),test_rows_near_candidate=sum(p['Distance_m']<=45 for p in gpsmatch),received_frames_near_candidate=len(ss),unique_candidates_with_received_RSSI=len(aa),historically_calibrated_candidates_in_new_observations=sum(x['old'] for x in aa),candidate_fraction_of_twin_pct=100*len(aa)/N,unique_candidate_gateway_pairs=len(aggregated))
        visited=set(p['Node_ID'] for p in gpsmatch if p['Distance_m']<=45)
        summary['route45_summary'].update(unique_candidates_visited=len(visited),new_candidate_locations_with_RSSI=sum(not x['old'] for x in aa),union_historical_and_route_RSSI_candidates=int(v.sum())+sum(not x['old'] for x in aa))
        for old in (True,False):
            subset=[x for x in aa if x['old']==old]
            route_metrics.append(dict(radius_m=45,Gateway='network_cal_old_locations' if old else 'network_cal_new_locations',unit='candidate_median_of_best_received',**metrics([x['cal'] for x in subset],[x['obs'] for x in subset])))
        write('red_mejor_enlace_105_candidatos.csv',aa)
write('exactitud_ruta2_provisional.csv',route_metrics);write('medianas_por_interseccion_gateway_45m.csv',aggregated)
summary['route2_comparisons']=route_metrics
examples=[]
for gw in ('gateway1','gateway2'):
    cand=[x for x in aggregated if x['Gateway']==gw and x['n_frames']>=2 and x['median_matching_distance_m']<=15]
    for x in sorted(cand,key=lambda x:abs(x['Median_observed_uplink_dBm']-x['Predicted_raw_dBm']),reverse=True)[:5]:examples.append(dict(**x,Residual_obs_minus_pred_dB=x['Median_observed_uplink_dBm']-x['Predicted_raw_dBm']))
write('ejemplos_intersecciones.csv',examples)
summary['route_received_links_below_model_threshold']={gw:sum(p['Predicted_raw_dBm']<-131 for p in pairs if p['Gateway']==gw and p['Match_distance_m']<=45) for gw in ('gateway1','gateway2')}
street_metrics=[]
for radius in (15,30,45,60):
    for gw in ('gateway1','gateway2'):
        ss=[p for p in pairs if p['Match_distance_m']<=radius and p['Gateway']==gw and p['Node_ID'] not in ('1','2')];groups=collections.defaultdict(list)
        for p in ss:groups[p['Node_ID']].append(p)
        aa=[dict(pred=vv[0]['Predicted_raw_dBm'],obs=float(np.median([x['Measured_uplink_dBm'] for x in vv]))) for vv in groups.values()]
        street_metrics.append(dict(radius_m=radius,series=gw,unit='street_candidate_gateway_pair',**metrics([x['pred'] for x in aa],[x['obs'] for x in aa])))
    ss=[p for p in network if p['Match_distance_m']<=radius and p['Node_ID'] not in ('1','2')];groups=collections.defaultdict(list)
    for p in ss:groups[p['Node_ID']].append(p)
    aa=[dict(Node_ID=k,raw=vv[0]['Raw_best_pred_dBm'],cal=vv[0]['Calibrated_best_pred_dBm'],obs=float(np.median([x['Best_received_RSSI_dBm'] for x in vv])),old=vv[0]['Node_in_historical_calibration']) for k,vv in groups.items()]
    for label in ('raw','cal'):
        street_metrics.append(dict(radius_m=radius,series='best_'+label,unit='street_candidate_best_received',**metrics([x[label] for x in aa],[x['obs'] for x in aa])))
    if radius==45:
        summary['route45_street_candidates']=dict(n=len(aa),old=sum(x['old'] for x in aa),new=sum(not x['old'] for x in aa),fraction_of_2628_street_candidates_pct=100*len(aa)/(N-2))
        summary['route45_street_candidates'].update(historical_RSSI_street_candidates=int(v[2:].sum()),union_historical_and_route_RSSI_street_candidates=int(v[2:].sum())+sum(not x['old'] for x in aa))
        for old in (True,False):
            ss=[x for x in aa if x['old']==old]
            street_metrics.append(dict(radius_m=45,series='best_cal_old_locations' if old else 'best_cal_new_locations',unit='street_candidate_best_received',**metrics([x['cal'] for x in ss],[x['obs'] for x in ss])))
        write('red_mejor_enlace_intersecciones_sin_anclas.csv',aa)
summary['street_only_comparisons']=street_metrics;write('exactitud_sin_anclas.csv',street_metrics)
(O/'resumen_exactitud.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:val for k,val in summary.items() if k not in ('route2_comparisons','street_only_comparisons')},ensure_ascii=False,indent=2));print('ROUTE45_STREETS',json.dumps([x for x in street_metrics if x['radius_m']==45],ensure_ascii=False,indent=2))
