function MDPI_FieldTester_Master_Suite(varargin)
    % =========================================================================
    % TESIS DOCTORAL - UNIVERSIDAD POLITÉCNICA SALESIANA
    % SUITE MAESTRA DE VALIDACIÓN EMPÍRICA Y CALIBRACIÓN MULTI-ESCENARIO
    % Modelo: 3D-M-SAGA (Gemelo Digital Morfológico 3D + Ray/Clutter Tuning)
    % Autor: Santiago Alejandro Acurio Maldonado
    % Director: Dr. Erwin Jairo Sacoto Cabrera
    % Ciudad de Estudio: Ambato, Ecuador (Gateway: Milesight UG67 en Paltas y Autachi)
    % =========================================================================
    clc; close all; warning('off', 'all');
    
    disp('=========================================================================');
    disp('   TESIS DOCTORAL: SUITE MAESTRA DE VALIDACIÓN EMPÍRICA LoRaWAN 3D      ');
    disp('   Universidad Politécnica Salesiana - Ambato, Ecuador                  ');
    disp('=========================================================================');
    
    %% 1. CONFIGURACIÓN PARAMÉTRICA ADAPTATIVA
    % Permite ejecución interactiva, por argumentos o en lote comparativo
    if nargin >= 3
        BandPlan_in = varargin{1};
        SF_in       = varargin{2};
        Ptx_in      = varargin{3};
        if nargin >= 4, RunMode = varargin{4}; else, RunMode = 'SINGLE'; end
    else
        % Configuración por defecto (o interactiva)
        RunMode = 'MENU';
    end
    
    if strcmp(RunMode, 'MENU')
        disp(' Seleccione el modo de ejecución:');
        disp('   [1] Escenario Calibrado Ecuador: US915 / AU915, SF7, Ptx = 20 dBm (Campaña 10-Octubre / Rutas Rectificadas)');
        disp('   [2] Escenario Transición Ecuador: US915 / AU915, SF9, Ptx = 20 dBm (Campaña 10-Octubre)');
        disp('   [3] Escenario Inicial Histórico: AU915 Estándar, SF9, Ptx = 30 dBm (Campaña AU915 / Movimiento Cotidiano)');
        disp('   [4] EJECUTAR BARRIDO COMPARATIVO COMPLETO (Genera tabla maestra y figuras para la Tesis)');
        
        try
            choice = input(' Ingrese opción [1-4] (Presione Enter para opción 1): ');
        catch
            choice = 1;
        end
        if isempty(choice), choice = 1; end
        
        switch choice
            case 1
                Run_Single_Scenario('US915', 7, 20, '10octubre');
            case 2
                Run_Single_Scenario('US915', 9, 20, '10octubre');
            case 3
                Run_Single_Scenario('AU915', 9, 30, 'AU915');
            case 4
                Run_Full_Comparative_Suite();
            otherwise
                Run_Single_Scenario('US915', 7, 20, '10octubre');
        end
    elseif strcmp(RunMode, 'ALL_COMPARATIVE')
        Run_Full_Comparative_Suite();
    else
        Run_Single_Scenario(BandPlan_in, SF_in, Ptx_in, 'AUTO');
    end
end

%% ========================================================================
%% FUNCIÓN DE EJECUCIÓN DE ESCENARIO INDIVIDUAL
%% ========================================================================
function Res = Run_Single_Scenario(BandPlan, SF_val, Ptx_val, DataFolderChoice)
    disp(' ');
    fprintf(' -> [INICIANDO ESCENARIO] Banda: %s | SF: %d | Ptx: %d dBm | Datos: %s\n', ...
        BandPlan, SF_val, Ptx_val, DataFolderChoice);
    
    %% Configuración del Hardware y Gateway
    City = struct('Name','Ambato, ECU', 'Lat',-1.2417, 'Lon',-78.6197, 'Alt',2580);
    GW_Lat = -1.25164; GW_Lon = -78.62765; GW_Alt_GPS = 2694; GW_Height = 6.0;
    Tester_Height = 1.5; 
    
    HW.BandPlan = BandPlan;
    HW.Freq = 915.0; % MHz
    HW.Ptx = Ptx_val; % dBm
    HW.Gain = 2.15; % dBi
    HW.SF = SF_val;
    
    % Sensibilidades según Spreading Factor (SX1302 / SX1262 a 125 kHz)
    if HW.SF == 7
        HW.Sens = -125.0; % dBm
    elseif HW.SF == 8
        HW.Sens = -128.0;
    elseif HW.SF == 9
        HW.Sens = -130.0;
    elseif HW.SF == 10
        HW.Sens = -133.0;
    else
        HW.Sens = -136.0;
    end
    
    % Directorio de salida
    fecha_hora = datestr(now, 'yyyymmdd_HHMMSS');
    folder_out = sprintf('Master_Validation_%s_SF%d_%ddBm_%s', HW.BandPlan, HW.SF, HW.Ptx, fecha_hora);
    if ~exist(folder_out, 'dir'), mkdir(folder_out); end
    
    %% 1. Cargar Gemelo Digital Topológico (Offline Ultra-Rápido)
    disp('    -> [FASE 1] Cargando Gemelo Digital Morfológico 3D de Ambato...');
    T_Twin = Load_Digital_Twin_Local(City);
    if isempty(T_Twin), error('No se pudo cargar el Gemelo Digital.'); end
    N_nodes = height(T_Twin);
    
    % Proyectar coordenadas del Gateway
    dist_geo = sqrt((T_Twin.Lat - GW_Lat).^2 + (T_Twin.Lon - GW_Lon).^2);
    [~, GW_Idx] = min(dist_geo);
    T_Twin.Altitude_m(GW_Idx) = GW_Alt_GPS;
    writetable(T_Twin, fullfile(folder_out, 'DigitalTwin_Base_Model.csv'));
    
    %% 2. Ingesta Inteligente de Datos del Field Tester
    disp('    -> [FASE 2] Ingesta y filtrado de telemetría del Field Tester...');
    [Lat_emp, Lon_emp, RSSI_emp, SNR_emp, Metadata_emp] = Load_FieldTester_Campaign(DataFolderChoice, HW.SF);
    N_emp = length(Lat_emp);
    fprintf('       Total puntos empíricos procesados: %d\n', N_emp);
    if N_emp == 0
        warning('No se encontraron puntos válidos para esta configuración.');
        Res = []; return;
    end
    
    %% 3. Motor de Propagación 3D-M-SAGA (Log-Distance + Clutter + Topo 3D)
    disp('    -> [FASE 3] Computando motor de propagación tridimensional 3D-M-SAGA...');
    R_earth = 6371000;
    X_gw = deg2rad(GW_Lon - City.Lon) * R_earth * cosd(City.Lat);
    Y_gw = deg2rad(GW_Lat - City.Lat) * R_earth;
    
    % Pérdida en espacio libre a 1 metro
    L0 = 20*log10(HW.Freq) - 27.55; 
    
    % Distancia euclidiana tridimensional
    d_3d = sqrt((T_Twin.X_m - X_gw).^2 + (T_Twin.Y_m - Y_gw).^2 + (T_Twin.Altitude_m - (GW_Alt_GPS + GW_Height)).^2);
    d_3d(d_3d < 1) = 1.0;
    
    % Calibración morfológica de exponentes y atenuación de clutter
    n_path = 2.65 * ones(N_nodes, 1);
    L_clut = 2.5 * ones(N_nodes, 1);
    
    idx_den = (T_Twin.Clutter == "Dense Urban");
    n_path(idx_den) = 2.85; 
    L_clut(idx_den) = 5.0;
    
    idx_prk = (T_Twin.Clutter == "Park/Periphery");
    n_path(idx_prk) = 2.35; 
    L_clut(idx_prk) = 0.0;
    
    % Obstrucción orográfica 3D (SRTM)
    diff_alt = (GW_Alt_GPS + GW_Height) - T_Twin.Altitude_m;
    L_topo = zeros(N_nodes, 1);
    c_idx = (diff_alt < -10); % Cuando el relieve supera al Gateway por cresta
    L_topo(c_idx) = min(8.0 * log10(abs(diff_alt(c_idx))), 20.0);
    
    % RSSI Teórico estimado por el Gemelo Digital
    EIRP = HW.Ptx + HW.Gain;
    RSSI_Theo = EIRP - L0 - (10.0 .* n_path .* log10(d_3d)) - L_clut - L_topo;
    
    % Exportar Cobertura 3D calculada
    T_Twin.Theoric_RSSI = RSSI_Theo;
    T_Twin.Is_Covered = (RSSI_Theo >= HW.Sens);
    writetable(T_Twin, fullfile(folder_out, 'Cobertura3DMSAGA.csv'));
    
    %% 4. Emparejamiento Topológico Z-Snapping & Fusión de Datos
    disp('    -> [FASE 4] Emparejamiento espacial Z-Snapping...');
    X_emp = deg2rad(Lon_emp - City.Lon) * R_earth * cosd(City.Lat);
    Y_emp = deg2rad(Lat_emp - City.Lat) * R_earth;
    
    Tolerance_Radius = 50.0; % metros de tolerancia de intersección
    Empirical_Matched = nan(N_nodes, 1);
    Empirical_Count = zeros(N_nodes, 1);
    
    for i = 1:N_emp
        dists = sqrt((T_Twin.X_m - X_emp(i)).^2 + (T_Twin.Y_m - Y_emp(i)).^2);
        [min_d, n_idx] = min(dists);
        if min_d <= Tolerance_Radius
            if isnan(Empirical_Matched(n_idx))
                Empirical_Matched(n_idx) = RSSI_emp(i);
            else
                Empirical_Matched(n_idx) = max(Empirical_Matched(n_idx), RSSI_emp(i)); % Retener mejor enlace
            end
            Empirical_Count(n_idx) = Empirical_Count(n_idx) + 1;
        end
    end
    
    valid_idx = ~isnan(Empirical_Matched);
    N_val = sum(valid_idx);
    fprintf('       Nodos validados por colocalización (1 a 1): %d\n', N_val);
    
    %% 5. Cómputo de Métricas Estadísticas (Estándar Doctoral / MDPI)
    if N_val > 0
        err = Empirical_Matched(valid_idx) - RSSI_Theo(valid_idx);
        RMSE = sqrt(mean(err.^2));
        MAE = mean(abs(err));
        
        % Similitud RF bajo margen de desvanecimiento log-normal (+/- 6 dB)
        sim_6db = (sum(abs(err) <= 6.0) / N_val) * 100.0;
        sim_10db = (sum(abs(err) <= 10.0) / N_val) * 100.0;
        
        % Coincidencia de estado de cobertura
        emp_cov = Empirical_Matched(valid_idx) >= HW.Sens;
        theo_cov = RSSI_Theo(valid_idx) >= HW.Sens;
        TP = sum(emp_cov & theo_cov);
        FP = sum(~emp_cov & theo_cov);
        FN = sum(emp_cov & ~theo_cov);
        TN = sum(~emp_cov & ~theo_cov);
        Accuracy_Cov = ((TP + TN) / N_val) * 100.0;
    else
        RMSE = NaN; MAE = NaN; sim_6db = NaN; sim_10db = NaN; Accuracy_Cov = NaN;
    end
    
    fprintf('       [MÉTRICAS] RMSE: %.2f dB | MAE: %.2f dB | Similitud RF (±6dB): %.1f%%\n', ...
        RMSE, MAE, sim_6db);
    
    %% 6. Exportación de Tablas de Evidencia para la Tesis
    T_Match = table(T_Twin.Street_1(valid_idx), T_Twin.Street_2(valid_idx), ...
                    T_Twin.Lat(valid_idx), T_Twin.Lon(valid_idx), ...
                    T_Twin.Altitude_m(valid_idx), T_Twin.Clutter(valid_idx), ...
                    round(RSSI_Theo(valid_idx), 2), round(Empirical_Matched(valid_idx), 2), ...
                    round(err, 2), ...
                    'VariableNames', {'Calle_1','Calle_2','Lat','Lon','Altitud_m','Clutter','RSSI_Teorico_dBm','RSSI_Empirico_dBm','Error_dB'});
    writetable(T_Match, fullfile(folder_out, 'CoincidenciasAnalisis.csv'));
    
    % Guardar resumen del escenario
    Res = struct();
    Res.Escenario = sprintf('%s_SF%d_%ddBm', HW.BandPlan, HW.SF, HW.Ptx);
    Res.BandPlan = HW.BandPlan;
    Res.SF = HW.SF;
    Res.Ptx = HW.Ptx;
    Res.Sensibilidad = HW.Sens;
    Res.Total_Nodos = N_nodes;
    Res.Nodos_Validados = N_val;
    Res.RMSE = RMSE;
    Res.MAE = MAE;
    Res.Similitud_6dB = sim_6db;
    Res.Similitud_10dB = sim_10db;
    Res.Exactitud_Cobertura = Accuracy_Cov;
    Res.FolderOut = folder_out;
    
    %% 7. Generación de Figuras de Alta Resolución
    Generate_Publication_Figures(T_Twin, valid_idx, Empirical_Matched, RSSI_Theo, GW_Lat, GW_Lon, Res, folder_out);
    
    % Generar reporte de texto para capítulo de tesis
    Generate_Thesis_Summary_Text(Res, folder_out);
end

%% ========================================================================
%% FUNCIÓN BARRIDO COMPARATIVO COMPLETO (3 ESCENARIOS PARA LA TESIS)
%% ========================================================================
function Run_Full_Comparative_Suite()
    disp(' ');
    disp('=========================================================================');
    disp(' INICIANDO BARRIDO COMPARATIVO COMPLETO (EVIDENCIAS CAPÍTULO 4 TESIS)     ');
    disp('=========================================================================');
    
    resA = Run_Single_Scenario('AU915', 9, 30, 'AU915');      % Escenario Inicial Histórico
    resB = Run_Single_Scenario('US915', 9, 20, '10octubre');    % Escenario Transición Ecuador SF9
    resC = Run_Single_Scenario('US915', 7, 20, '10octubre');    % Escenario Optimizado Calibrado SF7
    
    % Tabla Maestra Comparativa
    T_Master = table({resA.Escenario; resB.Escenario; resC.Escenario}, ...
                     [resA.BandPlan; resB.BandPlan; resC.BandPlan], ...
                     [resA.SF; resB.SF; resC.SF], ...
                     [resA.Ptx; resB.Ptx; resC.Ptx], ...
                     [resA.Sensibilidad; resB.Sensibilidad; resC.Sensibilidad], ...
                     [resA.Nodos_Validados; resB.Nodos_Validados; resC.Nodos_Validados], ...
                     [resA.RMSE; resB.RMSE; resC.RMSE], ...
                     [resA.MAE; resB.MAE; resC.MAE], ...
                     [resA.Similitud_6dB; resB.Similitud_6dB; resC.Similitud_6dB], ...
                     [resA.Exactitud_Cobertura; resB.Exactitud_Cobertura; resC.Exactitud_Cobertura], ...
                     'VariableNames', {'Escenario','Banda','SF','Ptx_dBm','Sensibilidad_dBm','Nodos_Validados','RMSE_dB','MAE_dB','Similitud_6dB_pct','Exactitud_Cobertura_pct'});
    
    folder_comp = sprintf('Comparative_Thesis_Results_%s', datestr(now, 'yyyymmdd_HHMMSS'));
    mkdir(folder_comp);
    writetable(T_Master, fullfile(folder_comp, 'Resumen_Comparativo_Escenarios.csv'));
    
    % Exportar código LaTeX listo para insertar en tesis.tex
    fid = fopen(fullfile(folder_comp, 'tabla_comparativa_tesis.tex'), 'w', 'n', 'UTF-8');
    fprintf(fid, '%% Tabla generada automáticamente por MDPI_FieldTester_Master_Suite\n');
    fprintf(fid, '\\begin{table}[htbp]\n\\centering\n');
    fprintf(fid, '\\caption{Comparación empírica multi-escenario en Ambato: impacto de banda, potencia y factor de propagación.}\n');
    fprintf(fid, '\\label{tab:comparativa_escenarios_fieldtester}\n\\small\n');
    fprintf(fid, '\\begin{tabular}{lcccccc}\n\\toprule\n');
    fprintf(fid, '\\textbf{Escenario de Prueba} & \\textbf{Banda} & \\textbf{Ptx (dBm)} & \\textbf{SF} & \\textbf{Nodos} & \\textbf{RMSE (dB)} & \\textbf{Similitud ($\\pm 6$ dB)} \\\\\n\\midrule\n');
    fprintf(fid, 'A: Histórico No Dirigido & %s & %d & %d & %d & %.2f & %.1f\\%% \\\\\n', resA.BandPlan, resA.Ptx, resA.SF, resA.Nodos_Validados, resA.RMSE, resA.Similitud_6dB);
    fprintf(fid, 'B: Adaptado Ecuador SF9 & %s & %d & %d & %d & %.2f & %.1f\\%% \\\\\n', resB.BandPlan, resB.Ptx, resB.SF, resB.Nodos_Validados, resB.RMSE, resB.Similitud_6dB);
    fprintf(fid, '\\textbf{C: Optimizado Calibrado SF7} & \\textbf{%s} & \\textbf{%d} & \\textbf{%d} & \\textbf{%d} & \\textbf{%.2f} & \\textbf{%.1f\\%%} \\\\\n', resC.BandPlan, resC.Ptx, resC.SF, resC.Nodos_Validados, resC.RMSE, resC.Similitud_6dB);
    fprintf(fid, '\\bottomrule\n\\end{tabular}\n\\end{table}\n');
    fclose(fid);
    
    disp(' ');
    disp('=========================================================================');
    disp(' TABLA MAESTRA COMPARATIVA GENERADA CON ÉXITO:');
    disp(T_Master);
    fprintf(' Guardada en: %s\n', folder_comp);
    disp('=========================================================================');
end

%% ========================================================================
%% INGESTA ROBUSTA Y LIMPIEZA DE ARCHIVOS DEL FIELD TESTER
%% ========================================================================
function [Lat_all, Lon_all, RSSI_all, SNR_all, Metadata] = Load_FieldTester_Campaign(FolderChoice, FilterSF)
    Lat_all = []; Lon_all = []; RSSI_all = []; SNR_all = []; Metadata = {};
    
    root_ft = fullfile(pwd, 'FieldTester');
    if strcmp(FolderChoice, 'AU915')
        target_dir = fullfile(root_ft, 'AU915');
    elseif strcmp(FolderChoice, '10octubre')
        target_dir = fullfile(root_ft, '10octubre');
    else
        % AUTO
        if exist(fullfile(root_ft, '10octubre'), 'dir')
            target_dir = fullfile(root_ft, '10octubre');
        else
            target_dir = fullfile(root_ft, 'AU915');
        end
    end
    
    if ~exist(target_dir, 'dir')
        warning('El directorio %s no existe.', target_dir);
        return;
    end
    
    csv_files = dir(fullfile(target_dir, '*.csv'));
    fprintf('       Escaneando %d archivos en %s...\n', length(csv_files), target_dir);
    
    for f = 1:length(csv_files)
        fname = csv_files(f).name;
        if contains(lower(fname), 'noise'), continue; end % omitir analizador de ruido
        
        fpath = fullfile(target_dir, fname);
        try
            opts = detectImportOptions(fpath);
            opts.VariableNamingRule = 'preserve';
            T = readtable(fpath, opts);
            vnames = lower(string(T.Properties.VariableNames));
            
            lat_idx = find(contains(vnames, 'lat'), 1);
            lon_idx = find(contains(vnames, 'lon') | contains(vnames, 'lng'), 1);
            rssi_idx = find(contains(vnames, 'rssi') & ~contains(vnames, 'rssis'), 1);
            snr_idx = find(contains(vnames, 'snr'), 1);
            sf_idx = find(contains(vnames, 'sf'), 1);
            
            if isempty(lat_idx) || isempty(lon_idx) || isempty(rssi_idx), continue; end
            
            lat_col = T.Properties.VariableNames{lat_idx};
            lon_col = T.Properties.VariableNames{lon_idx};
            rssi_col = T.Properties.VariableNames{rssi_idx};
            snr_col = ''; if ~isempty(snr_idx), snr_col = T.Properties.VariableNames{snr_idx}; end
            sf_col = ''; if ~isempty(sf_idx), sf_col = T.Properties.VariableNames{sf_idx}; end
            
            for r = 1:height(T)
                lat_raw = string(T{r, lat_col});
                lon_raw = string(T{r, lon_col});
                rssi_raw = string(T{r, rssi_col});
                
                % Descartar paquetes fallidos ('-' o vacíos)
                if lat_raw == "-" || lon_raw == "-" || rssi_raw == "-" || ismissing(lat_raw) || ismissing(rssi_raw)
                    continue;
                end
                
                rssi_val = str2double(rssi_raw);
                if isnan(rssi_val) || rssi_val > 0 || rssi_val < -140, continue; end
                
                % Parsear latitud y longitud con soporte para formatos con °W, °S
                lat_val = Parse_Coordinate(lat_raw);
                lon_val = Parse_Coordinate(lon_raw);
                if isnan(lat_val) || isnan(lon_val), continue; end
                
                % Validar coordenadas dentro del marco geográfico de Ambato
                if lat_val < -1.35 || lat_val > -1.15 || lon_val < -78.75 || lon_val > -78.50
                    continue;
                end
                
                % Filtrar por Spreading Factor si el archivo contiene dicha columna
                if ~isempty(sf_col)
                    sf_str = upper(string(T{r, sf_col}));
                    if FilterSF == 7 && ~contains(sf_str, 'SF7') && (contains(sf_str, 'SF9') || contains(sf_str, 'SF10'))
                        continue;
                    elseif FilterSF == 9 && ~contains(sf_str, 'SF9') && contains(sf_str, 'SF7')
                        continue;
                    end
                end
                
                snr_val = 0;
                if ~isempty(snr_col)
                    s_str = string(T{r, snr_col});
                    if s_str ~= "-" && ~ismissing(s_str), snr_val = str2double(s_str); end
                end
                
                Lat_all = [Lat_all; lat_val]; %#ok<AGROW>
                Lon_all = [Lon_all; lon_val]; %#ok<AGROW>
                RSSI_all = [RSSI_all; rssi_val]; %#ok<AGROW>
                SNR_all = [SNR_all; snr_val]; %#ok<AGROW>
            end
        catch
        end
    end
end

function val = Parse_Coordinate(str_val)
    str_val = char(str_val);
    tokens = regexp(str_val, '([0-9.]+)\s*°?\s*([NSEW])', 'tokens');
    if ~isempty(tokens)
        num = str2double(tokens{1}{1});
        hem = tokens{1}{2};
        if hem == 'S' || hem == 'W', num = -num; end
        val = num;
        return;
    end
    val = str2double(str_val);
end

%% ========================================================================
%% CARGA OFFLINE DEL GEMELO DIGITAL
%% ========================================================================
function T = Load_Digital_Twin_Local(City)
    % Buscar DigitalTwin_Base_Model.csv en subcarpetas o raíz
    found_dt = dir(fullfile(pwd, '**', 'DigitalTwin_Base_Model.csv'));
    if ~isempty(found_dt)
        dt_path = fullfile(found_dt(1).folder, found_dt(1).name);
        disp(['       Cargando Gemelo Digital precalculado desde: ', dt_path]);
        T = readtable(dt_path);
        return;
    end
    
    % Si no existe, construirlo desde mapa_ambato.json
    local_json = fullfile(pwd, 'mapa_ambato.json');
    if exist(local_json, 'file')
        disp('       Construyendo Gemelo Digital desde mapa_ambato.json...');
        data = jsondecode(fileread(local_json));
        c_nodes = containers.Map('KeyType','uint64','ValueType','any'); 
        c_names = containers.Map('KeyType','uint64','ValueType','any');
        
        for i=1:length(data.elements)
            e = data.elements(i); if iscell(data.elements), e=e{1}; end 
            if strcmp(e.type, 'node'), c_nodes(e.id) = [e.lat, e.lon];
            elseif strcmp(e.type, 'way') && isfield(e, 'nodes')
                st = "Unnamed Road"; 
                if isfield(e, 'tags') && isfield(e.tags, 'name'), st = string(e.tags.name); end
                for k=1:length(e.nodes)
                    nid = e.nodes(k); if iscell(e.nodes), nid=nid{1}; end
                    if isKey(c_names, nid), c_names(nid) = [c_names(nid), st]; else, c_names(nid) = st; end
                end
            end
        end
        
        lat = []; lon = []; c1 = []; c2 = []; keys_n = c_names.keys;
        for k = 1:length(keys_n)
            nid = keys_n{k}; noms = unique(c_names(nid)); 
            if length(noms) >= 2 && isKey(c_nodes, nid)
                coords = c_nodes(nid); lat = [lat; coords(1)]; lon = [lon; coords(2)]; 
                c1 = [c1; noms(1)]; c2 = [c2; noms(2)]; 
            end
        end
        
        N = length(lat);
        R_earth = 6371000;
        X_m = deg2rad(lon - City.Lon) * R_earth * cosd(City.Lat);
        Y_m = deg2rad(lat - City.Lat) * R_earth;
        Alt_m = 2650 * ones(N, 1);
        
        % Asignar clutter simple
        clutter = strings(N, 1);
        for i = 1:N
            d = sqrt(X_m(i)^2 + Y_m(i)^2);
            if d < 1200, clutter(i) = "Dense Urban";
            elseif d < 2400, clutter(i) = "Residential";
            else, clutter(i) = "Park/Periphery";
            end
        end
        
        T = table((1:N)', c1, c2, lat, lon, X_m, Y_m, Alt_m, clutter, ...
            'VariableNames', {'Node_ID','Street_1','Street_2','Lat','Lon','X_m','Y_m','Altitude_m','Clutter'});
    else
        T = [];
    end
end

%% ========================================================================
%% GENERADOR DE FIGURAS DOCTORALES
%% ========================================================================
function Generate_Publication_Figures(T_Twin, valid_idx, Empirical_Matched, RSSI_Theo, GW_Lat, GW_Lon, Res, folder_out)
    try
        % FIGURA 1: MAPA 2D OVERLAY (Gemelo Digital vs Telemetría Real)
        fig1 = figure('Visible', 'off', 'Position', [100, 100, 950, 750], 'Color', 'w');
        scatter(T_Twin.Lon, T_Twin.Lat, 14, RSSI_Theo, 'filled', 'MarkerFaceAlpha', 0.4);
        hold on;
        colormap(jet(256));
        c = colorbar; c.Label.String = 'RSSI (dBm)'; c.Label.FontSize = 11;
        caxis([-125, -60]);
        
        % Puntos empíricos medidos
        scatter(T_Twin.Lon(valid_idx), T_Twin.Lat(valid_idx), 45, Empirical_Matched(valid_idx), ...
                'filled', 'MarkerEdgeColor', 'k', 'LineWidth', 1.2);
        
        % Gateway UG67
        plot(GW_Lon, GW_Lat, 'p', 'MarkerSize', 16, 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'k', 'LineWidth', 1.5);
        
        grid on; box on;
        xlabel('Longitud WGS84 (°)'); ylabel('Latitud WGS84 (°)');
        title(sprintf('Validación Empírica 3D-M-SAGA · Ambato | %s | RMSE = %.2f dB', Res.Escenario, Res.RMSE), ...
            'FontSize', 12, 'FontWeight', 'bold');
        legend({'3D-M-SAGA Teórico', 'Field Tester (Empírico)', 'Gateway UG67 (Paltas)'}, 'Location', 'northwest');
        saveas(fig1, fullfile(folder_out, 'Figura_Overlay_Empirico_2D.png'));
        close(fig1);
        
        % FIGURA 2: SCATTER PLOT TEÓRICO VS EMPÍRICO (DISPERSIÓN Y ERROR)
        if sum(valid_idx) > 2
            fig2 = figure('Visible', 'off', 'Position', [150, 150, 750, 600], 'Color', 'w');
            y_emp = Empirical_Matched(valid_idx);
            x_theo = RSSI_Theo(valid_idx);
            
            scatter(x_theo, y_emp, 40, 'b', 'filled', 'MarkerFaceAlpha', 0.7); hold on;
            plot([-125, -50], [-125, -50], 'k--', 'LineWidth', 1.5); % Línea 1:1
            plot([-125, -50], [-125+6, -50+6], 'r:', 'LineWidth', 1.2); % +6 dB
            plot([-125, -50], [-125-6, -50-6], 'r:', 'LineWidth', 1.2); % -6 dB
            
            grid on; box on;
            xlabel('RSSI Teórico 3D-M-SAGA (dBm)', 'FontSize', 11);
            ylabel('RSSI Empírico Field Tester (dBm)', 'FontSize', 11);
            title(sprintf('Dispersión y Margen de Error RF · %s (RMSE = %.2f dB | MAE = %.2f dB)', ...
                Res.Escenario, Res.RMSE, Res.MAE), 'FontSize', 11, 'FontWeight', 'bold');
            legend({'Mediciones Intersección', 'Línea Ideal (1:1)', 'Margen Desvanecimiento ±6 dB'}, 'Location', 'southeast');
            saveas(fig2, fullfile(folder_out, 'Figura_Scatter_Error_RF.png'));
            close(fig2);
        end
    catch
    end
end

function Generate_Thesis_Summary_Text(Res, folder_out)
    txt_path = fullfile(folder_out, 'Resumen_Estadistico_Capitulo4.txt');
    fid = fopen(txt_path, 'w', 'n', 'UTF-8');
    fprintf(fid, '========================================================\n');
    fprintf(fid, ' RESUMEN ESTADÍSTICO PARA EL CAPÍTULO 4 DE LA TESIS     \n');
    fprintf(fid, '========================================================\n');
    fprintf(fid, 'Escenario: %s\n', Res.Escenario);
    fprintf(fid, 'Banda de Frecuencia: %s (915 MHz)\n', Res.BandPlan);
    fprintf(fid, 'Potencia Field Tester: %d dBm\n', Res.Ptx);
    fprintf(fid, 'Spreading Factor: SF%d (Sensibilidad: %.1f dBm)\n', Res.SF, Res.Sensibilidad);
    fprintf(fid, 'Total Nodos Evaluados: %d\n', Res.Total_Nodos);
    fprintf(fid, 'Nodos Validados Empíricamente: %d\n', Res.Nodos_Validados);
    fprintf(fid, 'Error Cuadrático Medio (RMSE): %.2f dB\n', Res.RMSE);
    fprintf(fid, 'Error Absoluto Medio (MAE): %.2f dB\n', Res.MAE);
    fprintf(fid, 'Similitud RF (Margen ± 6 dB): %.2f %%\n', Res.Similitud_6dB);
    fprintf(fid, 'Similitud RF (Margen ± 10 dB): %.2f %%\n', Res.Similitud_10dB);
    fprintf(fid, 'Concordancia Estado Cobertura: %.2f %%\n', Res.Exactitud_Cobertura);
    fclose(fid);
end
