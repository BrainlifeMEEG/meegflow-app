"""FIR bandpass filtering, mirroring filter-raw's exact Raw.filter() call.

meegflow's built-in bandpass_filter step is hardcoded to IIR (two-pass
Butterworth) and to data['raw'] only. This step uses MNE's FIR filter design
(zero-phase, windowed-sinc) instead, on whichever instance is requested.
"""
import re


def fir_filter(data, step_config):
    """Apply an MNE FIR bandpass (and optional notch) filter.

    Args:
        data: Pipeline data dict. Must contain step_config['instance'].
        step_config: Step parameters, passed straight through to
            `<instance>.filter(...)` (and `.notch_filter(...)` if `notch` is
            given), mirroring filter-raw/main.py:
            - instance (str): Key in data to filter. Default 'raw'.
            - l_freq, h_freq (float or None)
            - notch (str or None): Comma/space-separated notch frequencies.
            - picks
            - filter_length (str or int): Default 'auto'.
            - l_trans_bandwidth, h_trans_bandwidth: Default 'auto'.
            - method (str): Default 'fir'.
            - iir_params
            - phase (str): Default 'zero'.
            - fir_window (str): Default 'hamming'.
            - fir_design (str): Default 'firwin'.
            - skip_by_annotation
            - pad

    Returns:
        Updated data dict with data[instance] filtered in place.

    Raises:
        ValueError: If the requested instance is not in data.
    """
    instance = step_config.get('instance', 'raw')
    if instance not in data:
        raise ValueError(f"fir_filter step requires '{instance}' in data")

    inst = data[instance]

    notch = step_config.get('notch')
    if notch:
        if isinstance(notch, str):
            notch = [float(x) for x in re.split(r'\W+', notch) if x]
        inst.notch_filter(freqs=notch, picks=step_config.get('picks'))

    inst.filter(
        picks=step_config.get('picks'),
        l_freq=step_config.get('l_freq'),
        h_freq=step_config.get('h_freq'),
        filter_length=step_config.get('filter_length', 'auto'),
        l_trans_bandwidth=step_config.get('l_trans_bandwidth', 'auto'),
        h_trans_bandwidth=step_config.get('h_trans_bandwidth', 'auto'),
        method=step_config.get('method', 'fir'),
        iir_params=step_config.get('iir_params'),
        phase=step_config.get('phase', 'zero'),
        fir_window=step_config.get('fir_window', 'hamming'),
        fir_design=step_config.get('fir_design', 'firwin'),
        skip_by_annotation=step_config.get('skip_by_annotation', ('edge', 'bad_acq_skip')),
        pad=step_config.get('pad', 'reflect_limited'),
    )

    data['preprocessing_steps'].append({
        'step': 'fir_filter',
        'instance': instance,
        'l_freq': step_config.get('l_freq'),
        'h_freq': step_config.get('h_freq'),
    })

    return data
