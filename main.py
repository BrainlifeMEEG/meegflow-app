#!/usr/bin/env python3
"""
This app will run meegflow using the information in the config.json

"""

# Copyright (c) 2026 brainlife.io
#
# Authors:
# - Maximilien Chaumon (https://github.com/dnacombo)

import os
import shutil
import yaml
import sys
import mne
import matplotlib.pyplot as plt
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

sys.path.insert(0, os.path.join(SCRIPT_DIR, 'brainlife_utils'))
from brainlife_utils import (
    load_config,
    setup_matplotlib_backend,
    ensure_output_dirs,
    create_product_json,
    add_info_to_product,
    add_image_to_product,
    require_config_keys
)

setup_matplotlib_backend()

# Load configuration
config_data = load_config(str(SCRIPT_DIR / "config.json"))
require_config_keys(config_data, ['raw'])

# Extract raw path(s) and yaml content. 'raw' is a single-file input by
# default, but becomes a list of paths when the app's input is configured as
# multi (e.g. to concatenate multiple runs) -- normalize to a list either way.
raw_paths = config_data.get('raw')
if isinstance(raw_paths, str):
    raw_paths = [raw_paths]
yaml_content = config_data.get('yaml')

# When there's more than one raw file, sort by each file's own recording
# start time (not the order brainlife happened to hand them to us -- a
# multi-input's path order isn't guaranteed stable across runs/resubmissions
# of "the same" inputs). concatenate_recordings just concatenates
# data['all_raw'] in whatever order the reader found the files, so an
# unstable input order would silently concatenate runs in a different
# sequence between runs -- different epoch numbering, different indices for
# any hardcoded epoch-drop lists, a differently-ordered ICA input matrix --
# even with a fixed ICA random_state.
if len(raw_paths) > 1:
    raw_paths = sorted(
        raw_paths,
        key=lambda p: mne.io.read_raw_fif(p, preload=False, verbose=False).info['meas_date'],
    )

# Stage every raw file into its own subdirectory under a common root, each
# named identically ("raw.fif"), regardless of how brainlife happened to lay
# out the (possibly differently-nested) input paths. This is what lets a
# single wildcard glob pattern below group all of them into one recording.
staging_root = Path("in_raw")
if staging_root.exists():
    shutil.rmtree(staging_root)
for i, p in enumerate(raw_paths):
    run_dir = staging_root / f"run{i}"
    run_dir.mkdir(parents=True)
    (run_dir / "raw.fif").symlink_to(Path(p).resolve())

# Write YAML content to config.yaml file
config_yaml_path = SCRIPT_DIR / "config.yaml"
if yaml_content:
    with open(config_yaml_path, 'w') as f:
        f.write(yaml_content)

print(f"Raw data path(s): {raw_paths}")
print(f"Staged {len(raw_paths)} raw file(s) under: {staging_root.resolve()}")
print(f"Config YAML path: {config_yaml_path}")
print("Starting MEEGFlow pipeline execution...")

# Import meegflow from source code
meegflow_src_path = os.path.join(SCRIPT_DIR, "meegflow", "src")
if not Path(meegflow_src_path).exists():
    print(f"Error: meegflow source not found at {meegflow_src_path}")
    print("Please update meegflow_src_path in this script to point to your meegflow/src directory")
    sys.exit(1)

sys.path.insert(0, meegflow_src_path)

try:
    from meegflow import MEEGFlowPipeline
    from meegflow.readers import GlobReader
except ImportError as e:
    print(f"Error importing meegflow: {e}")
    sys.exit(1)

# Load configuration
try:
    with open(config_yaml_path, 'r') as f:
        config = yaml.safe_load(f)
except yaml.YAMLError as e:
    mark = getattr(e, 'problem_mark', None)
    if mark is not None:
        with open(config_yaml_path, 'r') as f:
            lines = f.readlines()
        offending_line = lines[mark.line].rstrip('\n') if mark.line < len(lines) else ''
        pointer = ' ' * mark.column + '^'
        detail = (
            f"YAML syntax error in the pipeline config at line {mark.line + 1}, "
            f"column {mark.column + 1}:\n{offending_line}\n{pointer}\n"
            f"{getattr(e, 'problem', None) or str(e)}\n"
            "Check indentation: every step under 'pipeline:' must start with the "
            "same number of spaces before its '- name: ...' (mixing e.g. 1 and 2 "
            "spaces between steps is a common cause)."
        )
    else:
        detail = f"YAML syntax error in the pipeline config: {e}"
    print(detail)
    error_product_items = []
    add_info_to_product(error_product_items, detail, 'error')
    create_product_json(error_product_items)
    sys.exit(1)

# custom_steps_folder is resolved by meegflow against the process's current
# working directory at pipeline-run time, not against this YAML's location --
# make it absolute here so it loads reliably regardless of invocation context.
if config.get('custom_steps_folder'):
    config['custom_steps_folder'] = str(SCRIPT_DIR / config['custom_steps_folder'])

# Create a glob reader matching every staged raw.fif under staging_root. The
# wildcard (no {variable}) makes the reader group all of them into a single
# recording's data['all_raw'], ready for concatenate_recordings.
reader = GlobReader(
    data_root=str(staging_root),
    pattern="*/raw.fif"
)

# meegflow writes into its own BIDS-derivatives-style scratch tree under this
# root; the flat, brainlife-conventional outputs are assembled from it below.
scratch_root = Path("out_dir")

# meegflow's own step loop already logs "Executing step: <name>" via MNE's
# logger, which flushes to stdout on every call -- pin the log level here so
# that per-step status keeps reaching the web UI's live status line even if
# it's ever lowered elsewhere (e.g. via the stderr noise-reduction guidance
# in agent-instructions.md, which would otherwise silently suppress it).
mne.set_log_level('INFO')

product_items = []
try:
    # Pipeline construction validates the config's step names against the
    # built-in + custom step registry and raises immediately on an unknown
    # one (e.g. a typo'd step name) -- keep it inside this try so that shows
    # up as a clear product.json error instead of a raw traceback.
    pipeline = MEEGFlowPipeline(
        reader=reader,
        output_root=str(scratch_root),
        config=config
    )

    results = pipeline.run_pipeline(extension=".fif", io_backend="read_raw_fif")

    print("\nPipeline execution completed!")
    print(f"Results: {results}")

    # This app processes exactly one recording per task (the glob reader
    # matches a single raw.fif), so a single result is expected. Results are
    # grouped as {recording_key: [result_dict]}.
    result = next(iter(results.values()))[0]

    if 'error' in result:
        raise RuntimeError(result['error'])

    raw_file = result.get('raw_file')
    epochs_file = result.get('epochs_file')
    html_report = result.get('html_report')

    # meegflow's own run_pipeline() only copies a fixed set of keys (raw_file,
    # epochs_file, json_report, html_report, n_epochs, preprocessing_steps)
    # from the per-recording data dict into its returned results -- custom
    # steps' own data['evoked_files'] never makes it through, so look for
    # what they actually wrote on disk instead of trusting the results dict.
    evoked_dir = scratch_root / 'evoked'
    evoked_files = [str(p) for p in evoked_dir.glob('*.fif')] if evoked_dir.is_dir() else []

    if raw_file is None and epochs_file is None:
        raise ValueError(
            "Pipeline completed but produced neither a raw nor an epochs "
            "output. Add a 'save_clean_instance' step to the pipeline YAML."
        )

    # Flatten meegflow's nested output into the brainlife-conventional flat
    # filenames matching this app's registered outputs (out_raw/raw.fif,
    # out_epo/meg-epo.fif, out_report/report.html, out_evoked/*.fif). Only
    # the outputs the configured pipeline actually produced are created.
    if raw_file is not None:
        ensure_output_dirs('out_raw')
        shutil.move(raw_file, os.path.join('out_raw', 'raw.fif'))

    if epochs_file is not None:
        ensure_output_dirs('out_epo')
        shutil.move(epochs_file, os.path.join('out_epo', 'meg-epo.fif'))

    if html_report is not None:
        ensure_output_dirs('out_report')
        shutil.move(html_report, os.path.join('out_report', 'report.html'))

    if evoked_files:
        ensure_output_dirs('out_evoked')
        for f in evoked_files:
            shutil.move(f, os.path.join('out_evoked', os.path.basename(f)))

    # meegflow's scratch tree has served its purpose; it isn't a declared
    # output itself.
    shutil.rmtree(scratch_root, ignore_errors=True)
    shutil.rmtree(staging_root, ignore_errors=True)

    add_info_to_product(product_items, "MEEGFlow pipeline execution completed", 'success')

    # Quick-look preview plot from the final saved output: PSD for a raw
    # output, averaged ERP butterfly for an epochs output.
    ensure_output_dirs('out_figs')
    if raw_file is not None:
        raw = mne.io.read_raw_fif(os.path.join('out_raw', 'raw.fif'), preload=True, verbose=False)
        fig = raw.compute_psd(verbose=False).plot(show=False)
        psd_path = os.path.join('out_figs', 'psd.png')
        fig.savefig(psd_path)
        plt.close(fig)
        add_image_to_product(product_items, 'Power spectral density', filepath=psd_path)

    if epochs_file is not None:
        epochs = mne.read_epochs(os.path.join('out_epo', 'meg-epo.fif'), preload=True, verbose=False)
        fig = epochs.average().plot(spatial_colors=True, show=False)
        erp_path = os.path.join('out_figs', 'erp.png')
        fig.savefig(erp_path)
        plt.close(fig)
        add_image_to_product(product_items, 'Averaged ERP', filepath=erp_path)

    create_product_json(product_items)
except Exception as e:
    print(f"Error running pipeline: {e}")
    add_info_to_product(product_items, f"MEEGFlow pipeline failed: {e}", 'error')
    create_product_json(product_items)
    sys.exit(1)