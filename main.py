#!/usr/bin/env python3
"""
This app will run meegflow using the information in the config.json

"""

# Copyright (c) 2026 brainlife.io
#
# Authors:
# - Maximilien Chaumon (https://github.com/dnacombo)

import os
import json
import yaml
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Create output directory
os.makedirs("out_dir", exist_ok=True)

# Read config.json
config_json_path = SCRIPT_DIR / "config.json"
with open(config_json_path, 'r') as f:
    config_data = json.load(f)

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
data_root = "/home/maximilien.chaumon/liensNet/analyse/BRAINLIFE/datasets/"
reader = GlobReader(
    data_root=data_root,
    pattern="*.fif"
)

# Initialize pipeline
pipeline = MEEGFlowPipeline(
    reader=reader,
    output_root="out_dir",
    config=config
)

# Run preprocessing
try:
    results = pipeline.run_pipeline(extension=".fif")
    
    # Print results
    print("\nPipeline execution completed!")
    print(f"Results: {results}")
except Exception as e:
    print(f"Error running pipeline: {e}")
    sys.exit(1) 