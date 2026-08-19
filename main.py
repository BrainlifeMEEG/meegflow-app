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
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

sys.path.insert(0, os.path.join(SCRIPT_DIR, 'brainlife_utils'))
from brainlife_utils import (
    load_config,
    ensure_output_dirs,
    create_product_json,
    add_info_to_product,
    require_config_keys
)

# Load configuration
config_data = load_config(str(SCRIPT_DIR / "config.json"))
require_config_keys(config_data, ['raw'])

# Extract raw path and yaml content
raw_path = config_data.get('raw')
yaml_content = config_data.get('yaml')

# Get absolute path and directory of raw data file
raw_abs_path = (Path(raw_path).parent.resolve() / Path(raw_path).name) if raw_path else None
raw_dir = raw_abs_path.parent if raw_abs_path else None

# Write YAML content to config.yaml file
config_yaml_path = SCRIPT_DIR / "config.yaml"
if yaml_content:
    with open(config_yaml_path, 'w') as f:
        f.write(yaml_content)

print(f"Raw data path: {raw_abs_path}")
print(f"Raw data directory: {raw_dir}")
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
with open(config_yaml_path, 'r') as f:
    config = yaml.safe_load(f)

# Create a glob reader for .fif files
data_root = str(raw_dir)
reader = GlobReader(
    data_root=data_root,
    pattern="raw.fif"
)

# meegflow writes into its own BIDS-derivatives-style scratch tree under this
# root; the flat, brainlife-conventional outputs are assembled from it below.
scratch_root = Path("out_dir")

# Initialize pipeline
pipeline = MEEGFlowPipeline(
    reader=reader,
    output_root=str(scratch_root),
    config=config
)

# Run preprocessing
product_items = []
try:
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

    if raw_file is None and epochs_file is None:
        raise ValueError(
            "Pipeline completed but produced neither a raw nor an epochs "
            "output. Add a 'save_clean_instance' step to the pipeline YAML."
        )

    # Flatten meegflow's nested output into the brainlife-conventional flat
    # filenames matching this app's registered outputs (out_raw/raw.fif,
    # out_epo/meg-epo.fif, out_report/report.html). Only the outputs the
    # configured pipeline actually produced are created.
    if raw_file is not None:
        ensure_output_dirs('out_raw')
        shutil.move(raw_file, os.path.join('out_raw', 'raw.fif'))

    if epochs_file is not None:
        ensure_output_dirs('out_epo')
        shutil.move(epochs_file, os.path.join('out_epo', 'meg-epo.fif'))

    if html_report is not None:
        ensure_output_dirs('out_report')
        shutil.move(html_report, os.path.join('out_report', 'report.html'))

    # meegflow's scratch tree has served its purpose; it isn't a declared
    # output itself.
    shutil.rmtree(scratch_root, ignore_errors=True)

    add_info_to_product(product_items, "MEEGFlow pipeline execution completed", 'success')
    add_info_to_product(product_items, f"Results: {results}")
    create_product_json(product_items)
except Exception as e:
    print(f"Error running pipeline: {e}")
    add_info_to_product(product_items, f"MEEGFlow pipeline failed: {e}", 'error')
    create_product_json(product_items)
    sys.exit(1)