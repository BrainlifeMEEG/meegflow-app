"""Correctness-aware epoching, porting epoch/main.py's logic verbatim.

Links each stimulus event to the subject's response via mne.epochs.make_metadata,
infers whether the response matches the target implied by the stimulus name,
and optionally keeps only correct-response trials.
"""
import mne


def epoch_with_correctness(data, step_config):
    """Create stimulus-locked epochs with response-correctness metadata/filtering.

    Args:
        data: Pipeline data dict. Must contain 'raw'.
        step_config: Step parameters:
            - tmin, tmax (float): Epoch time window.
            - metadata_tmin, metadata_tmax (float): Window for linking
              stimulus/response events via mne.epochs.make_metadata.
            - event_id_condition_mapping (str): "name-id,name-id,..." string,
              same format as the epoch app's config.
            - event1kw (str): Keyword identifying stimulus-type event names
              (e.g. 'stimulus').
            - event2kw (str): Keyword identifying response-type event names
              (e.g. 'response').
            - assess_correctness (bool): Whether to infer response
              correctness. Default False.
            - use_correct (bool): Whether to keep only correct-response
              trials (requires assess_correctness). Default False.
            - picks: Channel picks for mne.Epochs. Default None.
            - stim_channel (str, optional): If given, find events from this
              stim channel instead of annotations.
            - baseline (2-element list/None): Default [None, 0].

    Returns:
        Updated data dict with data['epochs'] set.

    Raises:
        ValueError: If 'raw' is not in data, or no epochs were created.
    """
    if 'raw' not in data:
        raise ValueError("epoch_with_correctness requires 'raw' in data")

    raw = data['raw']
    tmin = step_config['tmin']
    tmax = step_config['tmax']
    picks = step_config.get('picks')
    if isinstance(picks, str) and picks not in ('all', None):
        picks = [p.strip() for p in picks.split(',')]
    elif picks == 'all':
        picks = None

    stim_channel = step_config.get('stim_channel')
    if not stim_channel:
        events, _ = mne.events_from_annotations(raw)
    else:
        events = mne.find_events(raw, stim_channel=stim_channel)

    event_id_condition = step_config['event_id_condition_mapping']
    event_id = dict(
        (x.strip(), int(y.strip()))
        for x, y in (element.rsplit('-', 1) for element in event_id_condition.split(','))
    )

    event1 = step_config['event1kw']
    event2 = step_config['event2kw']

    metadata_tmin = step_config.get('metadata_tmin', 0)
    metadata_tmax = step_config.get('metadata_tmax', 0)

    row_events = [k for k in event_id.keys() if event1 in k]
    keep_last = [event1, event2]
    event2_types = [k.split('/')[1] for k in event_id.keys() if event2 in k]

    metadata, events, event_id = mne.epochs.make_metadata(
        events=events, event_id=event_id,
        tmin=metadata_tmin, tmax=metadata_tmax, sfreq=raw.info['sfreq'],
        row_events=row_events, keep_last=keep_last,
    )

    assess_correctness = step_config.get('assess_correctness', False)
    if assess_correctness:
        targets = {}
        for event2_type in event2_types:
            for stim in row_events:
                if event2_type in stim:
                    target = stim.split('/')[-1].split('-')[0]
                    targets[event2_type] = target
                    break

        metadata[f'{event1}_type'] = 'unknown'
        for event2_type, target in targets.items():
            metadata.loc[metadata[f'last_{event1}'].str.contains(target), f'{event1}_type'] = event2_type

        metadata[f'{event2}_correct'] = False
        metadata.loc[
            metadata[f'{event1}_type'] == metadata[f'last_{event2}'],
            f'{event2}_correct',
        ] = True
    else:
        metadata[f'{event2}_correct'] = True

    baseline = step_config.get('baseline', [None, 0])
    baseline = tuple(baseline) if baseline is not None else None

    epochs = mne.Epochs(
        raw=raw, events=events, event_id=event_id, picks=picks,
        metadata=metadata, tmin=tmin, tmax=tmax, baseline=baseline, preload=True,
    )

    use_correct = step_config.get('use_correct', False)
    if use_correct and assess_correctness:
        epochs = epochs[f'{event2}_correct']

    if len(epochs) == 0:
        raise ValueError("No epochs were created. Check event_id and tmin/tmax parameters.")

    data['epochs'] = epochs
    data['preprocessing_steps'].append({
        'step': 'epoch_with_correctness',
        'tmin': tmin,
        'tmax': tmax,
        'n_epochs': len(epochs),
        'use_correct': use_correct,
        'assess_correctness': assess_correctness,
    })

    return data
