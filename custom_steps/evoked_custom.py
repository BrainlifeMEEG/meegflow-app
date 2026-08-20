"""Custom evoked-averaging steps mirroring evoked-averaged and average-erp.

meegflow has no built-in averaging step, and save_clean_instance doesn't
special-case Evoked/list-of-Evoked objects, so these steps compute and save
directly via mne.write_evokeds()/.save(), collecting the resulting paths in
data['evoked_files'] for main.py to flatten into the out_evoked output.
"""
import os

import mne


def average_by_event_type(data, step_config):
    """Average epochs per event type, mirroring evoked-averaged/main.py.

    Args:
        data: Pipeline data dict. Must contain 'epochs'.
        step_config: Step parameters:
            - picks: Channel picks for Epochs.average(). Default None.
            - method (str): Default 'mean'.

    Returns:
        Updated data dict with the saved file path appended to
        data['evoked_files'] (created if absent).

    Raises:
        ValueError: If 'epochs' is not in data.
    """
    if 'epochs' not in data:
        raise ValueError("average_by_event_type requires 'epochs' in data")

    epochs = data['epochs']
    evoked = epochs.average(
        picks=step_config.get('picks'),
        method=step_config.get('method', 'mean'),
        by_event_type=True,
    )

    deriv_root = data.derivatives_root('evoked')
    deriv_root.mkdir(parents=True, exist_ok=True)
    out_path = deriv_root / 'by_condition-ave.fif'
    mne.write_evokeds(out_path, evoked, overwrite=True)

    data.setdefault('evoked_files', []).append(str(out_path))
    data['preprocessing_steps'].append({
        'step': 'average_by_event_type',
        'n_conditions': len(evoked) if isinstance(evoked, list) else 1,
    })

    return data


def average_condition_group(data, step_config):
    """Average a named group of stimulus conditions, mirroring average-erp/main.py.

    Args:
        data: Pipeline data dict. Must contain 'epochs'.
        step_config: Step parameters:
            - average_all (bool): If True, average all epochs together.
              Default False.
            - stimulus_names (str): Comma-separated condition names to
              select and average together (used when not average_all).
            - condition (str): Name used for the output filename.
            - peaks (str, optional): Unused here (QC-plot only in the
              original app); accepted for config parity.

    Returns:
        Updated data dict with the saved file path appended to
        data['evoked_files'] (created if absent).

    Raises:
        ValueError: If 'epochs' is not in data.
    """
    if 'epochs' not in data:
        raise ValueError("average_condition_group requires 'epochs' in data")

    epochs = data['epochs']
    condition = step_config['condition']

    if step_config.get('average_all', False):
        evo = epochs.average()
    else:
        stimuli = [s.strip() for s in step_config['stimulus_names'].split(',')]
        evo = epochs[stimuli].average()

    deriv_root = data.derivatives_root('evoked')
    deriv_root.mkdir(parents=True, exist_ok=True)
    out_path = deriv_root / f'{condition}-ave.fif'
    evo.save(out_path, overwrite=True)

    data.setdefault('evoked_files', []).append(str(out_path))
    data['preprocessing_steps'].append({
        'step': 'average_condition_group',
        'condition': condition,
        'n_epochs_averaged': evo.nave,
    })

    return data
