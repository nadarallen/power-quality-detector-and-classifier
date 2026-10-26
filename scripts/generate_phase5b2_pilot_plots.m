% scripts/generate_phase5b2_pilot_plots.m
% Generates publication-grade physical validation plots for Phase 5B.2:
% 1. Dual-rate representation: 20 kHz vs 5 kHz on Notch (400 us) & Transient (2.2 kHz)
% 2. Fixed-reference sensor noise model validation across Normal, Sag, Swell, Interruption
% 3. ADC Quantization: 12-bit vs 14-bit resolution and residual error

function generate_phase5b2_pilot_plots()
    cur = fileparts(mfilename('fullpath'));
    root = fileparts(cur);
    fig_dir = fullfile(root, 'docs', 'figures', 'phase5b2_pilot');
    if ~exist(fig_dir, 'dir')
        mkdir(fig_dir);
    end
    proc_dir = fullfile(root, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'processed');

    % -------------------------------------------------------------
    % Figure 1: Dual-Rate Representation (Notch & Transient)
    % -------------------------------------------------------------
    f1 = figure('Visible', 'off', 'Position', [100 100 900 700]);

    % Subplot 1: Notch Zoom
    subplot(2, 1, 1);
    notch_file = fullfile(root, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'raw', 'P5B2_NOT_0073_abc_c01_mil.mat');
    if exist(notch_file, 'file')
        d_not = load(notch_file);
        t20k = (0:3999) * (200.0 / 4000.0); % ms
        t5k  = (0:999) * (200.0 / 1000.0);  % ms
        v20k = d_not.V_frame_20k(:, 1);
        v5k  = d_not.V_frame_5k(:, 1);

        m20 = (t20k >= 58.0 & t20k <= 66.0);
        m5  = (t5k  >= 58.0 & t5k  <= 66.0);

        plot(t20k(m20), v20k(m20), 'b-', 'LineWidth', 1.5); hold on;
        plot(t20k(m20), v20k(m20), 'bo', 'MarkerSize', 4, 'MarkerFaceColor', 'b');
        plot(t5k(m5), v5k(m5), 'r--s', 'LineWidth', 1.2, 'MarkerSize', 6, 'MarkerFaceColor', 'r');
        title('(a) Commutation Notch Representation: 20 kHz High-Res vs 5 kHz Canonical (400 \mu s width)', 'FontSize', 11, 'FontWeight', 'bold');
        xlabel('Time (ms)', 'FontSize', 10);
        ylabel('Phase A Voltage (pu)', 'FontSize', 10);
        grid on;
        legend({'20 kHz Branch (50 \mus step)', '20 kHz Samples (8 pts/notch)', '5 kHz Canonical (200 \mus step, 2 pts/notch)'}, 'Location', 'southeast', 'FontSize', 9);
    end

    % Subplot 2: Transient Zoom
    subplot(2, 1, 2);
    tra_file = fullfile(root, 'data', 'ieee9bus_60hz_phase5b_pilot_v2', 'raw', 'P5B2_TRA_0127_abc_c01_mil.mat');
    if exist(tra_file, 'file')
        d_tra = load(tra_file);
        t20k = (0:3999) * (200.0 / 4000.0);
        t5k  = (0:999) * (200.0 / 1000.0);
        v20k = d_tra.V_frame_20k(:, 1);
        v5k  = d_tra.V_frame_5k(:, 1);

        m20 = (t20k >= 38.0 & t20k <= 46.0);
        m5  = (t5k  >= 38.0 & t5k  <= 46.0);

        plot(t20k(m20), v20k(m20), 'b-', 'LineWidth', 1.5); hold on;
        plot(t20k(m20), v20k(m20), 'bo', 'MarkerSize', 3);
        plot(t5k(m5), v5k(m5), 'r--s', 'LineWidth', 1.2, 'MarkerSize', 6, 'MarkerFaceColor', 'r');
        title('(b) High-Frequency Transient Inception: 20 kHz vs 5 kHz Canonical (~2.2 kHz Ringing)', 'FontSize', 11, 'FontWeight', 'bold');
        xlabel('Time (ms)', 'FontSize', 10);
        ylabel('Phase A Voltage (pu)', 'FontSize', 10);
        grid on;
        legend({'20 kHz High-Res (Captures High-Freq Dynamics)', '20 kHz Samples', '5 kHz Decimated Branch (Anti-Aliased Chebyshev)'}, 'Location', 'northeast', 'FontSize', 9);
    end

    out1 = fullfile(fig_dir, 'dual_rate_notch_transient_comparison.png');
    saveas(f1, out1);
    close(f1);
    fprintf('[Plot] Saved: %s\n', out1);

    % -------------------------------------------------------------
    % Figure 2: Fixed-Reference Sensor Noise Validation
    % -------------------------------------------------------------
    f2 = figure('Visible', 'off', 'Position', [100 100 1000 700]);
    t = linspace(0, 0.05, 1000)'; % 50 ms
    w0 = 2 * pi * 60;
    v_norm = 0.5887 * sqrt(2) * sin(w0 * t);
    v_sag  = 0.2000 * sqrt(2) * sin(w0 * t);
    v_swl  = 0.8500 * sqrt(2) * sin(w0 * t);
    v_int  = 0.0050 * sqrt(2) * sin(w0 * t);

    p_nom = 0.5887019747712398^2;
    sigma_noise = sqrt(p_nom / (10^(52.0 / 10.0))); % ~0.0014787 pu
    rng(42);
    noise = randn(size(t)) * sigma_noise;

    cases = {
        'Normal (Nominal RMS = 0.589 pu)', v_norm, 1;
        'Sag (Deep Fault RMS = 0.200 pu)', v_sag, 2;
        'Swell (Capacitor RMS = 0.850 pu)', v_swl, 3;
        'Interruption (Residual RMS = 0.005 pu)', v_int, 4
    };

    t_ms = t * 1000;
    for k = 1:4
        subplot(2, 2, cases{k, 3});
        v_c = cases{k, 2};
        v_n = v_c + noise;
        plot(t_ms, v_n, 'Color', [0.2 0.5 0.8], 'LineWidth', 1.0); hold on;
        plot(t_ms, v_c, 'Color', [0.9 0.4 0.1], 'LineWidth', 1.5, 'LineStyle', '--');
        plot(t_ms, noise, 'Color', [0.2 0.7 0.2], 'LineWidth', 0.8);
        title(cases{k, 1}, 'FontSize', 10, 'FontWeight', 'bold');
        xlabel('Time (ms)', 'FontSize', 9);
        ylabel('Voltage (pu)', 'FontSize', 9);
        grid on;
        if k == 1
            legend({'Noisy (52 dB SNR)', 'Clean Signal', sprintf('Noise (\\sigma = %.6f pu)', sigma_noise)}, 'Location', 'northeast', 'FontSize', 8);
        end
    end
    sgtitle('Fixed-Reference AWGN Sensor Noise Validation (Constant \sigma_{noise} \approx 0.001479 pu across Disturbances)', 'FontSize', 12, 'FontWeight', 'bold');

    out2 = fullfile(fig_dir, 'fixed_reference_sensor_noise_comparison.png');
    saveas(f2, out2);
    close(f2);
    fprintf('[Plot] Saved: %s\n', out2);

    % -------------------------------------------------------------
    % Figure 3: ADC Quantization 12-bit vs 14-bit
    % -------------------------------------------------------------
    f3 = figure('Visible', 'off', 'Position', [100 100 900 650]);
    t = linspace(0, 0.02, 2000)'; % 20 ms
    v_clean = 0.5887 * sqrt(2) * sin(w0 * t);
    v_fs = 1.8;
    q12 = (2 * v_fs) / (2^12);
    q14 = (2 * v_fs) / (2^14);

    v_q12 = round(v_clean / q12) * q12;
    v_q14 = round(v_clean / q14) * q14;
    err12 = (v_clean - v_q12) * 1e3; % milli-pu
    err14 = (v_clean - v_q14) * 1e3;

    t_ms = t * 1000;
    zoom_m = (t_ms >= 3.5 & t_ms <= 5.5);

    subplot(2, 1, 1);
    plot(t_ms(zoom_m), v_clean(zoom_m), 'k-', 'LineWidth', 1.5); hold on;
    stairs(t_ms(zoom_m), v_q12(zoom_m), 'r-', 'LineWidth', 1.3);
    stairs(t_ms(zoom_m), v_q14(zoom_m), 'b-', 'LineWidth', 1.3);
    title('(a) Bipolar ADC Quantization Staircase Zoom (Crest Window)', 'FontSize', 11, 'FontWeight', 'bold');
    xlabel('Time (ms)', 'FontSize', 10);
    ylabel('Voltage (pu)', 'FontSize', 10);
    grid on;
    legend({'Analog Continuous (pu)', '12-bit ADC (q = 0.879 mpu)', '14-bit ADC (q = 0.220 mpu)'}, 'Location', 'south', 'FontSize', 9);

    subplot(2, 1, 2);
    plot(t_ms, err12, 'r-', 'LineWidth', 1.0); hold on;
    plot(t_ms, err14, 'b-', 'LineWidth', 1.0);
    yline(q12*1e3/2, 'r:', 'LineWidth', 1.0);
    yline(-q12*1e3/2, 'r:', 'LineWidth', 1.0);
    yline(q14*1e3/2, 'b:', 'LineWidth', 1.0);
    yline(-q14*1e3/2, 'b:', 'LineWidth', 1.0);
    title('(b) Quantization Residual Error e(t) = v(t) - v_{quant}(t) over Full Cycle', 'FontSize', 11, 'FontWeight', 'bold');
    xlabel('Time (ms)', 'FontSize', 10);
    ylabel('Residual Error (milli-pu)', 'FontSize', 10);
    grid on;
    legend({'12-bit Error (\pm q/2 = \pm 0.439 mpu)', '14-bit Error (\pm q/2 = \pm 0.110 mpu)'}, 'Location', 'northeast', 'FontSize', 9);

    out3 = fullfile(fig_dir, 'adc_quantization_12bit_vs_14bit.png');
    saveas(f3, out3);
    close(f3);
    fprintf('[Plot] Saved: %s\n', out3);

    fprintf('\nAll Phase 5B.2 plots generated successfully in: %s\n', fig_dir);
end
