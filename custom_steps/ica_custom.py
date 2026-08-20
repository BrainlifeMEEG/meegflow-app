"""Custom ICA fit/apply steps mirroring ICA-fit-epo and ICA-apply-epo exactly.

meegflow's built-in `ica` step doesn't support fit_params (needed for Extended
Infomax) and hardcodes different EOG/ECG rejection defaults than the real
apps use, so these steps port the real apps' logic instead of wrapping the
built-in.
"""
import mne
from mne.preprocessing import ICA


def ica_fit_custom(data, step_config):
    """Fit ICA on data['epochs'], mirroring ICA-fit-epo/main.py.

    Args:
        data: Pipeline data dict. Must contain 'epochs'.
        step_config: Step parameters:
            - n_components (int, optional): Falls back to
              min(50, sum(mne.compute_rank(epochs, rank='info').values()))
              when not given, matching the real app.
            - method (str): Default 'infomax'.
            - random_state (int, optional)
            - fit_params (str, optional): A string to eval() into a dict,
              e.g. "dict(extended=True)", matching the real app's own
              eval(config['fit_params']) pattern.
            - max_iter (optional)
            - allow_ref_meg (bool, optional)
            - noise_cov (optional)
            - l_freq, h_freq (float, optional): Pre-fit filter applied to a
              copy of the epochs (not the main data).

    Returns:
        Updated data dict with data['ica'] set to the fitted ICA object.

    Raises:
        ValueError: If 'epochs' is not in data.
    """
    if 'epochs' not in data:
        raise ValueError("ica_fit_custom requires 'epochs' in data")

    epo = data['epochs']

    l_freq = step_config.get('l_freq')
    h_freq = step_config.get('h_freq')
    if l_freq is not None or h_freq is not None:
        epo = epo.copy().filter(l_freq=l_freq, h_freq=h_freq)

    fit_params = None
    fit_params_str = step_config.get('fit_params')
    if fit_params_str is not None:
        fit_params = eval(fit_params_str)

    n_components = step_config.get('n_components')
    if not n_components:
        rank = mne.compute_rank(epo, rank='info')
        n_components = min(50, sum(rank.values()))

    ica_params = {
        'n_components': n_components,
        'random_state': step_config.get('random_state'),
        'method': step_config.get('method', 'infomax'),
    }
    if step_config.get('noise_cov') is not None:
        ica_params['noise_cov'] = step_config['noise_cov']
    if fit_params is not None:
        ica_params['fit_params'] = fit_params
    if step_config.get('max_iter') is not None:
        ica_params['max_iter'] = step_config['max_iter']
    if step_config.get('allow_ref_meg') is not None:
        ica_params['allow_ref_meg'] = step_config['allow_ref_meg']

    ica = ICA(**ica_params)
    ica.fit(epo)

    data['ica'] = ica
    data['preprocessing_steps'].append({
        'step': 'ica_fit_custom',
        'n_components': ica.n_components_,
        'method': ica_params['method'],
        'fit_params': fit_params,
    })

    return data


def ica_apply_custom(data, step_config):
    """Detect EOG/ECG components and apply ICA, mirroring ICA-apply-epo/main.py.

    Args:
        data: Pipeline data dict. Must contain 'epochs' and 'ica'.
        step_config: Step parameters:
            - exclude (list of int, optional): Component indices to exclude
              manually, in addition to any auto-detected ones.
            - reject_EOG (bool): Default False.
            - reject_ECG (bool): Default False.
            - EOG_chan, ECG_chan (str or int, optional): Channel name/index
              used for detection.

    Returns:
        Updated data dict with data['epochs'] ICA-cleaned in place.

    Raises:
        ValueError: If 'epochs' or 'ica' is not in data.
    """
    if 'epochs' not in data or 'ica' not in data:
        raise ValueError("ica_apply_custom requires 'epochs' and 'ica' in data")

    epo = data['epochs']
    ica = data['ica']

    exclude = list(step_config.get('exclude') or [])
    ica.exclude = exclude.copy()

    if step_config.get('reject_EOG', False):
        eog_idx, _ = ica.find_bads_eog(
            epo, ch_name=step_config.get('EOG_chan'), threshold=3.0,
            start=None, stop=None, l_freq=1, h_freq=10,
            reject_by_annotation=True, measure='zscore', verbose=None,
        )
        if eog_idx:
            ica.exclude = list(set(ica.exclude + eog_idx))

    if step_config.get('reject_ECG', False):
        ecg_idx, _ = ica.find_bads_ecg(
            epo, ch_name=step_config.get('ECG_chan'), threshold='auto',
            start=None, stop=None, l_freq=8, h_freq=16, method='ctps',
            reject_by_annotation=True, measure='zscore', verbose=None,
        )
        if ecg_idx:
            ica.exclude = list(set(ica.exclude + ecg_idx))

    ica.apply(epo)

    data['preprocessing_steps'].append({
        'step': 'ica_apply_custom',
        'excluded': sorted(ica.exclude),
    })

    return data
