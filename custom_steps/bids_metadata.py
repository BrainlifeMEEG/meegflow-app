"""Records BIDS-style recording identity (subject/session/run) into the
pipeline data dict and report, for traceability.
"""


def set_recording_metadata(data, step_config):
    """Seed data['subject']/['session'] (native meegflow report/BIDSPath
    fields) and log the full subject/session/run identity into
    data['preprocessing_steps'], since 'run' has no native meegflow field --
    a concatenated recording no longer corresponds to a single BIDS run.

    Args:
        data: Pipeline data dict.
        step_config: Step parameters:
            - subject (str or None)
            - session (str or None)
            - run (str or None): comma-joined list when multiple runs were
              concatenated.

    Returns:
        Updated data dict.
    """
    subject = step_config.get('subject')
    session = step_config.get('session')
    run = step_config.get('run')

    data['subject'] = subject
    data['session'] = session

    # preprocessing_steps entries must be dicts with a 'step' key -- other
    # meegflow report code (collect_bad_channels_from_steps, the ICA summary
    # lookup) indexes into each entry as a dict, a plain string breaks those.
    data.setdefault('preprocessing_steps', []).append({
        'step': 'set_recording_metadata',
        'subject': subject or 'unknown',
        'session': session or 'unknown',
        'run': run or 'unknown',
    })
    return data
