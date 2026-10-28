function run_benchmark(T,RSSI,Bin,Points,C,folder)
% Benchmark computacional de logicas heredadas; no prueba optimalidad en campo.
assert(size(RSSI,2)==height(T),'Trazable:Matrix','Matriz incompleta.');
[ok,anchors]=ismember([C.Gateways.NodeID],T.Node_ID);
assert(all(ok),'Trazable:Anchor','Ancla no identificada.');
assert(isequal(anchors,[1 2]),'Trazable:AnchorOrder', ...
    'Los algoritmos heredados requieren las anclas en las filas 1 y 2.');
demand=~ismember(T.Node_ID,[C.Gateways.NodeID]);B=Bin(demand,:);
assert(all(isfinite(RSSI(demand,:)),'all'),'Trazable:Matrix','Predicciones ausentes.');
previous=rng;restore=onCleanup(@()rng(previous));results=table();solutions=cell(C.BenchmarkRepetitions,4);
names=["Greedy heredado","K-medoids heredado","GA heredado","GA heredado + reparacion"];
for rep=1:C.BenchmarkRepetitions
    for algorithm=1:4
        seed=C.Seed+rep-1;rng(seed,'twister');tic;
        switch algorithm
            case 1,s=Run_Greedy_Original(B,C.TargetCoverage,anchors);
            case 2,s=Run_KMedoids_Original(Points,B,C.TargetCoverage,anchors);
            case 3,s=Run_GA_Original(B,C.TargetCoverage,false,anchors);
            case 4,s=Run_GA_Original(B,C.TargetCoverage,true,anchors);
        end
        elapsed=toc;map=sum(B(:,s),2);coverage=mean(map>=1);
        row=table(names(algorithm),rep,seed,nnz(s),100*coverage,100*mean(map==1), ...
            100*mean(map==2),100*mean(map>=3),coverage>=C.TargetCoverage,elapsed, ...
            C.ModelFingerprintSHA256,'VariableNames',{'Algorithm','Repetition','Seed','Gateways', ...
            'Coverage_pct','Exactly1_pct','Exactly2_pct','AtLeast3_pct','TargetAchieved','Time_s','ModelSHA256'});
        results=[results;row];solutions{rep,algorithm}=T.Node_ID(s); %#ok<AGROW>
    end
end
writetable(results,fullfile(folder,'benchmark_computacional.csv'));
save(fullfile(folder,'soluciones_benchmark.mat'),'solutions','C');
end

% A continuacion: funciones del script recibido, sin modificar su logica.

function sol = Run_Greedy_Original(BinM_3D, target, anchors)
    [N, C] = size(BinM_3D); sol = false(1, C); sol(anchors) = true; cov = any(BinM_3D(:, anchors), 2);
    while (sum(cov)/N) < target
        b_g = 0; b_n = -1; cands = find(~sol);
        for i = cands, g = sum(BinM_3D(:, i) & ~cov); if g > b_g, b_g = g; b_n = i; end, end
        if b_n > 0 && b_g > 0, sol(b_n) = true; cov = cov | BinM_3D(:, b_n); else, break; end
    end
end

function sol = Run_KMedoids_Original(Pts_3D, BinM_3D, target, anchors)
    [N, C] = size(BinM_3D); sol = false(1, C);
    D_euc = sqrt((Pts_3D(:,1) - Pts_3D(:,1)').^2 + (Pts_3D(:,2) - Pts_3D(:,2)').^2 + (Pts_3D(:,3) - Pts_3D(:,3)').^2);
    n_anc = length(anchors);
    for k = n_anc:2:30
        if k == n_anc, idx_m = anchors;
        else
            k_extra = k - n_anc; c_idx = zeros(k_extra, 1);
            min_dist = min(D_euc(:, anchors), [], 2); min_dist(anchors) = 0;
            for ki = 1:k_extra
                [~, next_c] = max(min_dist); c_idx(ki) = next_c;
                min_dist = min(min_dist, D_euc(:, next_c)); min_dist(c_idx(1:ki)) = 0;
            end
            medoids = unique([anchors(:); c_idx]);
            for iter_pam = 1:5
                [~, cluster_assign] = min(D_euc(:, medoids), [], 2); improved = false;
                for m = (n_anc+1):length(medoids)
                    members = find(cluster_assign == m); if isempty(members), continue; end
                    [~, best_l] = min(sum(D_euc(members, members), 2)); new_m = members(best_l);
                    if new_m ~= medoids(m) && ~ismember(new_m, anchors), medoids(m) = new_m; improved = true; end
                end
                if ~improved, break; end
            end
            idx_m = medoids;
        end
        if (sum(sum(BinM_3D(:, idx_m), 2) > 0) / N) >= target, sol(idx_m) = true; break; end
    end
    if sum(sol) == 0, sol(idx_m) = true; end
end

function [sol, fit_hist] = Run_GA_Original(BinM_3D, target, use_memetic, anchors)
    [N, C] = size(BinM_3D); p_size = 24; gen = 30; fit_hist = zeros(gen, 1);
    Pop = rand(p_size, C) < (10/C); Pop(:, anchors) = true; Pop(1,:) = Run_Greedy_Original(BinM_3D, target, anchors);
    for g = 1:gen
        Fit = zeros(p_size, 1);
        for i = 1:p_size
            mapa = sum(BinM_3D(:, find(Pop(i,:))), 2);
            c_tot = sum(mapa >= 1)/N; c_k2 = sum(mapa >= 2)/N; gw_cnt = sum(Pop(i,:));
            Fit(i) = (c_tot * 10000) + (c_k2 * 1000) - (gw_cnt * 50);
            if c_tot < target, Fit(i) = Fit(i) - 50000; end
        end
        [best_f, b] = max(Fit); fit_hist(g) = best_f; Best = Pop(b,:); NewPop = Pop;
        for i = 2:2:p_size
            p1 = Pop(randi(p_size),:); p2 = Pop(randi(p_size),:); mask = rand(1, C) > 0.5; c1 = p1; c1(mask) = p2(mask);
            if rand < 0.8
                if use_memetic, c1 = Smart_Repair_Original(c1, BinM_3D, target, anchors);
                else, mut = randi(C); if ~ismember(mut, anchors), c1(mut) = ~c1(mut); end; end
            end
            c1(anchors) = true; NewPop(i,:) = c1;
        end
        Pop = NewPop; Pop(1,:) = Best; Pop(:, anchors) = true;
    end
    sol = Pop(1,:);
end

function ind = Smart_Repair_Original(ind, BinM_3D, target, anchors)
    N = size(BinM_3D, 1); max_iter = 10; iter = 0; ind(anchors) = true;
    while iter < max_iter
        iter = iter + 1; idx = find(ind); mapa = sum(BinM_3D(:, idx), 2);
        if (sum(mapa >= 1) / N) >= target
            removable = setdiff(idx, anchors);
            if ~isempty(removable)
                unq = (mapa == 1); sc = sum(BinM_3D(:, removable) & unq, 1); [val, w] = min(sc);
                if val < 5, ind(removable(w)) = false; continue; end
            end
            break;
        else
            unc = (mapa == 0); cands = find(~ind); if isempty(cands), break; end
            gains = sum(BinM_3D(unc, cands), 1); [bg, best_idx] = max(gains);
            if bg > 0, ind(cands(best_idx)) = true; else, break; end
        end
    end
    ind(anchors) = true;
end

