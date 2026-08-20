"""Per-run preparation: montage, channel rename, bad channels, interpolation.

Mirrors mark-bad-raw + add-montage + interpolate, applied to each raw file
individually before concatenate_recordings, matching the real S05 rule chain
(interpolation needs each run's own channel positions/bads before merging).
"""
import re

import mne


def prepare_each_run(data, step_config):
    """Set montage, rename channels, mark bad channels, and interpolate them,
    on every raw in data['all_raw'] (in place), before concatenation.

    Args:
        data: Pipeline data dict. Must contain 'all_raw' (list of mne.io.Raw).
        step_config: Step parameters:
            - montage (str): Standard montage name. Default None (skip).
            - rename_channels (dict): {old_name: new_name} mapping. Default None (skip).
            - bads (str or list of str): Comma-separated bad channel names. A
              single str applies to every run; a list gives one str per run
              (matched by index into data['all_raw']). Default ''.
            - reset_bads (bool or list of bool): Clear existing bads first.
              Default False.
            - annotations (str or list of str): Multiline
              "onset,duration,description[,channels]" annotations, same
              format as mark-bad-raw. Default ''.

    Returns:
        Updated data dict with each data['all_raw'][i] mutated in place.

    Raises:
        ValueError: If 'all_raw' is not in data.
    """
    if 'all_raw' not in data:
        raise ValueError("prepare_each_run requires 'all_raw' in data")

    montage_name = step_config.get('montage')
    rename_channels = step_config.get('rename_channels')
    bads_param = step_config.get('bads', '')
    reset_bads_param = step_config.get('reset_bads', False)
    annotations_param = step_config.get('annotations', '')

    all_raw = data['all_raw']

    def _per_run(param, i):
        return param[i] if isinstance(param, list) else param

    for i, raw in enumerate(all_raw):
        # Only rename channels still under their old name -- lets this step
        # run idempotently on data that's already been renamed (e.g. a
        # 'with_montage' input that already went through this).
        applicable_renames = {}
        if rename_channels:
            applicable_renames = {old: new for old, new in rename_channels.items() if old in raw.ch_names}
            if applicable_renames:
                raw.rename_channels(applicable_renames)

        if montage_name:
            montage = mne.channels.make_standard_montage(montage_name)
            # Apply the same rename to the montage template so its channel
            # names line up with raw's regardless of whether raw was already
            # renamed coming in -- otherwise a channel renamed in raw but
            # still under its original name in the montage (e.g. the
            # reference channel, Cz -> E257) fails to match and gets left
            # with an invalid/missing position.
            if rename_channels:
                montage_renames = {old: new for old, new in rename_channels.items() if old in montage.ch_names}
                if montage_renames:
                    montage.rename_channels(montage_renames)
            raw.set_montage(montage, on_missing='ignore')

        if _per_run(reset_bads_param, i):
            raw.info['bads'] = []

        bads_str = _per_run(bads_param, i)
        if bads_str:
            bads = [b.strip() for b in bads_str.split(',')]
            bads = [b for b in bads if b]
            bads = [ch for ch in bads if ch in raw.ch_names]
            if bads:
                raw.info['bads'] = list(set(raw.info['bads']) | set(bads))

        annotations_str = _per_run(annotations_param, i)
        if annotations_str:
            lines = [re.split('[,;-]', n) for n in annotations_str.split('\n')]
            lines = [[part.strip() for part in n] for n in lines]

            onset, duration, description, ch_names = [], [], [], []
            for parts in lines:
                if len(parts) < 3:
                    continue
                parts = list(parts)
                onset.append(parts.pop(0))
                duration.append(parts.pop(0))
                description.append(parts.pop(0))
                ch_names.append(parts)

            annot = mne.Annotations(
                onset=onset, duration=duration, description=description,
                ch_names=ch_names,
            )
            raw.set_annotations(annot)

        if raw.info['bads']:
            raw.interpolate_bads()

        data['preprocessing_steps'].append({
            'step': 'prepare_each_run',
            'run_index': i,
            'montage': montage_name,
            'rename_channels': rename_channels,
            'bads': raw.info['bads'],
        })

    return data
