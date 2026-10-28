function C = config_campana_ambato()
% Cohorte C26-1400 (Ruta 1 por horario). R2 es una etiqueta interna heredada.
% No equivale a calibracion instrumental.
root = fileparts(mfilename('fullpath'));
C.InputRoot = fullfile(root, 'datos');
C.OutputRoot = fullfile(root, 'resultados');
C.CampaignID = "R2_20261026_desde1400_aproximado";
C.Role = "evaluation";
C.Mode = "legacy_audit"; % "physical_model" solo al completar condiciones.
C.MatchRadii_m = [15 30 45 60];
C.PrimaryRadius_m = 45;
C.AmbiguityMargin_m = 10; % Solo bandera; no elimina filas a posteriori.
C.TimePositionSemanticsVerified = false;
C.GNSSAccuracyVerified = false;
C.ClockCorrection_s = 0; % No corregir sin comprobar que significa Time en FT.
C.ExcludeInfrastructureFromMetrics = true;
C.Seed = 20261026;
C.MakeFigures = true;
C.RunBenchmark = false;
C.BenchmarkRepetitions = 5;
C.TargetCoverage = 0.92;
C.CalibrationFile = ""; % Coeficientes externos por gateway; nunca fit al evaluar.
% Identidad exacta de TTS; el numero de gateway NO es el indice MATLAB.
C.Gateways = struct('ID', {"gateway2", "gateway1"}, ...
    'Name', {"PUCESA", "Paltas"}, 'NodeID', {1, 2}, ...
    'RxGain_dBi', {NaN, NaN}, 'RxCableLoss_dB', {NaN, NaN}, ...
    'RxHeightAGL_m', {NaN, NaN}, 'HardwareSource', {"", ""});
C.Gateways(1).CoordinatesConfirmed=false;
C.Gateways(1).CoordinatesSource="Script anterior: -1.27458,-78.63920,2855 m; pendiente captura numerica PUCESA";
C.Gateways(2).CoordinatesConfirmed=true;
C.Gateways(2).CoordinatesSource="Capturas TTS Paltas y rx_metadata SOURCE_REGISTRY: -1.25160,-78.62772,2696 m; configuracion manual";
C.Gateways(1).InstallationFloor=12;
C.Gateways(2).InstallationFloor=3;
C.Gateways(1).FloorSource="Investigador: instalacion en piso 12; metros AGL pendientes";
C.Gateways(2).FloorSource="Investigador: instalacion a altura de tercer piso; metros AGL pendientes";
C.AntennaEvidence=struct('PhotographedGatewayAntennaGain_dBi',5, ...
    'Band_MHz',[902 928],'AppliesTo',"Antena fotografiada; confirmar las cuatro", ...
    'FT101Label',"LoRa 915; investigador declara ganancia tipica 2-3 dBi", ...
    'GatewayAntennasDeclared',2,'CombiningGainAssumed_dB',0);
% Estos valores son condiciones de referencia, no mediciones certificadas.
C.Model.TxPower_dBm = NaN; % Potencia conducida pendiente de documentar.
C.Model.FTExportPowerSetting_dBm = 30;
C.Model.PowerSettingInterpretationVerified = false;
C.Model.TxPowerSource = "CSV=30 dBm; ficha oficial FT101=22 dBm max a 915 MHz; discrepancia pendiente";
C.Model.TxGain_dBi = NaN;
C.Model.TxGainTypicalRange_dBi = [2.0 3.0];
C.Model.TxGainSource = "Investigador, 27/10/2026: rango tipico declarado; no medicion calibrada ni ficha especifica adjunta";
C.Model.TxGainScenarioMidpoint_dBi = 2.5; % Solo escenario central, no valor medido.
C.Model.TxCableLoss_dB = NaN;
C.Model.TxHeightAGL_m = 1.80;
C.Model.TxHeightSource = "Investigador: montaje en parrilla a 1.80 m aproximadamente; referencia de antena pendiente";
C.Model.TxHeightQuality = "approximate_declared_not_surveyed";
C.Model.TxHardwareSource = "Investigador: antena LoRa 915 original de fabrica; ganancia y perdidas no documentadas";
C.Model.CandidateRxGain_dBi = NaN;
C.Model.CandidateRxCableLoss_dB = NaN;
C.Model.CandidateRxHeightAGL_m = NaN;
C.Model.CandidateHardwareSource = "";
C.Model.Sensitivity_dBm = NaN; % Requiere criterio/ficha aplicable a SF9/BW125.
C.Model.SensitivitySource = "";
C.Model.VerticalDatum = "";
C.Model.GroundElevationCSV = fullfile(root, 'plantilla_elevaciones_por_coordenada.csv');
C.Model.ParametersDocumented = false;
C.Model.ReferenceFrequencyMHz = NaN; % Se obtiene de la mediana TTS recibida.
% Parametros heredados, no estimados de estas mediciones ni norma ITU-R.
C.Model.PathExponents = [3.8 3.2 3.5]; % Dense, Residential, Park/Periphery.
C.Model.ClutterLoss_dB = [18 0 12];
C.Model.UseLegacyTopographicPenalty = false;
C.Model.Version = "logdistance3D_uplink_scenario_v1";
C.Model.LegacyThreshold_dBm = -131; % Solo reproducir el criterio anterior.
end
