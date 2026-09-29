function Result = extract_PQD_features(t, Vabc, Iabc, t_start, t_end)
% extract_PQD_features
% Standards-oriented PQ feature extraction for IEEE 9-bus PQD project.
%
% Inputs:
%   t       - time vector
%   Vabc    - Nx3 three-phase voltage waveform in the existing
%             Bus 5 measurement pu representation
%   Iabc    - Nx3 three-phase current waveform
%   t_start - analysis window start time [s]
%   t_end   - analysis window end time [s]
%
% Output:
%   Result  - structure containing extracted PQ features

%% 1. Select analysis window

idx = (t >= t_start) & (t <= t_end);

tw = t(idx);

Va = Vabc(idx,1);
Vb = Vabc(idx,2);
Vc = Vabc(idx,3);

Ia = Iabc(idx,1);
Ib = Iabc(idx,2);
Ic = Iabc(idx,3);

%% 2. System parameters

f0 = 60;

Fs = 1 / mean(diff(tw));

%% 3. RMS voltage
% Existing Bus 5 voltage signal is normalized using the
% peak phase-to-ground base.
%
% Convert RMS of the logged signal to conventional RMS pu.

Vrms_raw = [
    sqrt(mean(Va.^2)), ...
    sqrt(mean(Vb.^2)), ...
    sqrt(mean(Vc.^2))
];

V_rms_pu_phase = Vrms_raw * sqrt(2);

V_rms_pu = mean(V_rms_pu_phase);

%% 4. Peak voltage

Vpeak_phase = [
    max(abs(Va)), ...
    max(abs(Vb)), ...
    max(abs(Vc))
];

V_peak_pu = mean(Vpeak_phase);

%% 5. Crest factor

Crest_phase = Vpeak_phase ./ Vrms_raw;

Crest_Factor = mean(Crest_phase);

%% 6. Harmonic analysis

N = length(Va);

x = Va - mean(Va);

X = fft(x);

P2 = abs(X/N);

P1 = P2(1:floor(N/2)+1);

if length(P1) > 2
    P1(2:end-1) = 2*P1(2:end-1);
end

f = Fs*(0:floor(N/2))/N;

% Fundamental

[~, k1] = min(abs(f - f0));

V1 = P1(k1);

%% 7. Harmonics 2nd through 50th

H = (2:50)';

H_freq = H * f0;

H_mag = zeros(length(H),1);

for k = 1:length(H)

    [~, kh] = min(abs(f - H_freq(k)));

    H_mag(k) = P1(kh);

end

THD_percent = sqrt(sum(H_mag.^2)) / V1 * 100;

%% 8. Dominant frequency

P1_noDC = P1;

P1_noDC(1) = 0;

[~, k_dom] = max(P1_noDC);

Dominant_Frequency_Hz = f(k_dom);

%% 9. System frequency

x_zc = Va - mean(Va);

zc = find(x_zc(1:end-1) <= 0 & x_zc(2:end) > 0);

t_zc = zeros(size(zc));

for k = 1:length(zc)

    n = zc(k);

    t1 = tw(n);
    t2 = tw(n+1);

    x1 = x_zc(n);
    x2 = x_zc(n+1);

    t_zc(k) = t1 - x1*(t2-t1)/(x2-x1);

end

T_cycles = diff(t_zc);

T_cycles = T_cycles(T_cycles > 0);

System_Frequency_Hz = 1 / mean(T_cycles);

%% 10. SNR

A = [
    sin(2*pi*f0*(tw-tw(1))) ...
    cos(2*pi*f0*(tw-tw(1))) ...
    ones(size(tw))
];

coef = A \ Va;

Va_fund = A * coef;

Va_residual = Va - Va_fund;

Signal_RMS = rms(Va_fund);

Residual_RMS = rms(Va_residual);

SNR_dB = 20*log10(Signal_RMS / Residual_RMS);

%% 11. Current RMS

Irms_phase = [
    sqrt(mean(Ia.^2)), ...
    sqrt(mean(Ib.^2)), ...
    sqrt(mean(Ic.^2))
];

I_rms_pu = mean(Irms_phase);

%% 12. Duration

% For Normal, this is a project/ML encoding.
% Actual disturbance duration will be calculated from
% detected disturbance start/end times.

Duration_ms = 0;

%% 13. Feature vector

Feature_Vector = [
    V_rms_pu, ...
    V_peak_pu, ...
    Crest_Factor, ...
    THD_percent, ...
    Duration_ms, ...
    Dominant_Frequency_Hz, ...
    System_Frequency_Hz, ...
    SNR_dB
];

%% 14. Store results

Result = struct();

Result.Class = "Normal";

Result.V_rms_pu = V_rms_pu;
Result.V_peak_pu = V_peak_pu;
Result.Crest_Factor = Crest_Factor;
Result.THD_percent = THD_percent;
Result.Duration_ms = Duration_ms;
Result.Dominant_Frequency_Hz = Dominant_Frequency_Hz;
Result.System_Frequency_Hz = System_Frequency_Hz;
Result.SNR_dB = SNR_dB;

Result.I_rms_pu = I_rms_pu;

Result.Window_Start_s = t_start;
Result.Window_End_s = t_end;
Result.Window_Duration_s = t_end - t_start;

Result.Sampling_Frequency_Hz = Fs;

Result.Feature_Vector = Feature_Vector;

end
