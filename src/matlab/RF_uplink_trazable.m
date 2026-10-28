function [RSSI,Bin,Points,E,C] = RF_uplink_trazable(T,C,R)
% Escenario log-distancia 3D uplink; no se presenta como ray tracing o ITU-R.
M=C.Model;
assert(M.ParametersDocumented,'Trazable:Parameters', ...
    'Completar/documentar condiciones fisicas antes de recalcular el gemelo.');
assert(M.PowerSettingInterpretationVerified,'Trazable:PowerInterpretation', ...
    'CSV 30 dBm y ficha FT101 22 dBm: resolver significado/potencia antes de modelar.');
assert(all([C.Gateways.CoordinatesConfirmed]),'Trazable:GatewayCoordinates', ...
    'Confirmar coordenadas de ambos sitios antes de recalcular.');
assert(all(R.FT_Power_dBm==M.FTExportPowerSetting_dBm),'Trazable:PowerCohort', ...
    'La potencia exportada cambia: separar cohortes o documentar su correspondencia fisica.');
required=[M.TxPower_dBm M.TxGain_dBi M.TxCableLoss_dB M.TxHeightAGL_m M.Sensitivity_dBm];
for k=1:numel(C.Gateways)
    required=[required C.Gateways(k).RxGain_dBi C.Gateways(k).RxCableLoss_dB C.Gateways(k).RxHeightAGL_m]; %#ok<AGROW>
end
if C.RunBenchmark
    required=[required M.CandidateRxGain_dBi M.CandidateRxCableLoss_dB M.CandidateRxHeightAGL_m];
end
assert(all(isfinite(required)),'Trazable:Hardware', ...
    'Hay ganancias, perdidas, alturas o sensibilidad desconocidas. No se sustituyen por cero.');
assert(M.TxHeightAGL_m>0 && all([C.Gateways.RxHeightAGL_m]>0), ...
    'Trazable:Height','Se requiere altura AGL positiva y documentada.');
assert(M.TxCableLoss_dB>=0 && all([C.Gateways.RxCableLoss_dB]>=0), ...
    'Trazable:Loss','Las perdidas de cable no pueden ser negativas.');
assert(strlength(M.VerticalDatum)>0 && strlength(M.SensitivitySource)>0, ...
    'Trazable:Datum','Documentar datum vertical y criterio de sensibilidad.');
assert(strlength(M.TxHardwareSource)>0 && all(strlength(string({C.Gateways.HardwareSource}))>0), ...
    'Trazable:HardwareSource','Documentar procedencia del montaje y de sus parametros.');
if C.RunBenchmark
    assert(strlength(M.CandidateHardwareSource)>0 && M.CandidateRxHeightAGL_m>0 && M.CandidateRxCableLoss_dB>=0, ...
        'Trazable:CandidateHardware','Documentar condiciones de sitios hipoteticos.');
end
assert(M.Sensitivity_dBm<0 && M.Sensitivity_dBm>-200, ...
    'Trazable:Sensitivity','Umbral RF invalido.');
assert(isfile(M.GroundElevationCSV),'Trazable:Elevation','Falta tabla de elevaciones por coordenada.');
E=readtable(M.GroundElevationCSV,'TextType','string');
names=string(E.Properties.VariableNames);
assert(all(ismember(["Latitude","Longitude","GroundElevation_m","VerticalDatum","ElevationSource"],names)), ...
    'Trazable:ElevationSchema','Columnas de elevacion incompletas.');
assert(all(isfinite(E.Latitude) & isfinite(E.Longitude) & isfinite(E.GroundElevation_m)), ...
    'Trazable:Elevation','Elevaciones ausentes: no usar cero ni cache por posicion.');
assert(all(~ismissing(E.VerticalDatum) & E.VerticalDatum==M.VerticalDatum), ...
    'Trazable:Datum','Datums verticales incompatibles o no documentados.');
assert(all(~ismissing(E.ElevationSource) & strlength(E.ElevationSource)>0), ...
    'Trazable:ElevationSource','Falta procedencia de elevacion.');
keys=compose('%.7f|%.7f',E.Latitude,E.Longitude);
assert(numel(unique(keys))==height(E),'Trazable:ElevationDuplicate','Coordenadas de elevacion duplicadas.');
nodekeys=compose('%.7f|%.7f',T.Latitude,T.Longitude);
[found,idx]=ismember(nodekeys,keys);
assert(all(found),'Trazable:ElevationMatch','Faltan cotas vinculadas a coordenadas del gemelo.');
E=E(idx,:);E.Node_ID=T.Node_ID;
origin=[mean(T.Latitude),mean(T.Longitude)];
x=deg2rad(T.Longitude-origin(2))*6371000*cosd(origin(1));
y=deg2rad(T.Latitude-origin(1))*6371000;
Points=[x y E.GroundElevation_m];
if ~isfinite(M.ReferenceFrequencyMHz),M.ReferenceFrequencyMHz=median(R.Frequency_Hz)/1e6;end
assert(M.ReferenceFrequencyMHz>0,'Trazable:Frequency','Frecuencia no valida.');
assert(all(isfinite(M.PathExponents) & M.PathExponents>0) && all(isfinite(M.ClutterLoss_dB) & M.ClutterLoss_dB>=0), ...
    'Trazable:Propagation','Parametros de propagacion no validos.');
% Clutter heredado por densidad OSM, no levantamiento fisico de edificios.
classes=["Dense Urban","Residential","Park/Periphery"];
[valid,classIndex]=ismember(T.Clutter_Class,classes);
assert(all(valid),'Trazable:Clutter','Clase no reconocida.');
nPath=reshape(M.PathExponents(classIndex),[],1);clutter=reshape(M.ClutterLoss_dB(classIndex),[],1);
N=height(T);RSSI=nan(N,N);Bin=false(N,N);
[known,anchorRows]=ismember([C.Gateways.NodeID],T.Node_ID);
assert(all(known),'Trazable:Anchor','Falta un gateway instalado en la referencia.');
if C.RunBenchmark,columns=1:N;else,columns=anchorRows;end
txZ=E.GroundElevation_m+M.TxHeightAGL_m;
for j=columns
    a=find(anchorRows==j);
    if isempty(a)
        rxGain=M.CandidateRxGain_dBi;rxLoss=M.CandidateRxCableLoss_dB;rxHeight=M.CandidateRxHeightAGL_m;
    else
        rxGain=C.Gateways(a).RxGain_dBi;rxLoss=C.Gateways(a).RxCableLoss_dB;rxHeight=C.Gateways(a).RxHeightAGL_m;
    end
    rxZ=E.GroundElevation_m(j)+rxHeight;
    distance=max(sqrt((x-x(j)).^2+(y-y(j)).^2+(txZ-rxZ).^2),1);
    topo=zeros(N,1);
    if M.UseLegacyTopographicPenalty
        delta=rxZ-txZ;v=delta < -15;topo(v)=min(10*log10(abs(delta(v))),35);
        v=delta>15 & distance>1800;topo(v)=min(12*log10(delta(v)),28);
    end
    L1m=20*log10(M.ReferenceFrequencyMHz)-27.55;
    RSSI(:,j)=M.TxPower_dBm+M.TxGain_dBi-M.TxCableLoss_dB+rxGain-rxLoss ...
        -L1m-10*nPath.*log10(distance)-clutter-topo;
    Bin(:,j)=RSSI(:,j)>=M.Sensitivity_dBm;
end
C.Model=M;
end
