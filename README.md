# app-meegflow

## Description

This app runs a configurable [MEEGFlow](https://github.com/BrainlifeMEEG/meegflow) preprocessing pipeline on MEG/EEG data. MEEGFlow executes a sequence of processing steps (e.g. concatenation, montage assignment, filtering, referencing, ICA, report generation) described by a YAML pipeline specification supplied through `config.json`. This allows a single app to run a full, user-defined preprocessing chain in one step.

## Inputs

- **raw**: One or more MNE raw data files in `.fif` format (each named `raw.fif` in its own containing directory, since each is located via a glob pattern). When more than one is given, they're concatenated into a single recording before the pipeline runs — see `run_order` below for how their order is determined.

## Outputs

Which of these are produced depends entirely on which steps the configured pipeline YAML runs;
each is only written if the corresponding step is present.

- **out_raw/raw.fif**: Preprocessed raw data, written when the pipeline runs `save_clean_instance` with `instance: raw`
- **out_epo/meg-epo.fif**: Preprocessed epochs, written when the pipeline runs `save_clean_instance` with `instance: epochs`
- **out_evoked/*.fif**: Averaged evoked data, written by the `average_by_event_type`/`average_condition_group` custom steps (see `custom_steps/` in the source), if used
- **out_report/report.html**: Interactive MNE Report, written when the pipeline runs `generate_html_report`
- **product.json**: Metadata describing pipeline execution status and results

## Configuration Parameters

### Required

- `raw`: Path to the input MNE raw data file(s) (`.fif` format, named `raw.fif`)
- `yaml`: A YAML-formatted string defining the MEEGFlow pipeline to execute. Each entry in the `pipeline` list specifies a processing step by `name` and its parameters.

### Optional

- `run_order`: How to order multiple `raw` inputs before concatenation. One of:
  - `as-is` (default): use the given input order untouched, no reordering.
  - `sort_by_meas_date`: sort by each file's own recording start time; the task fails with a clear error if any input is missing one, rather than silently falling back to something else.
  - `sort_by_tags`: sort by each file's brainlife dataset tags (best-effort — tags aren't guaranteed unique or sortable); the task fails with a clear error if any input has no tags.

  There is no automatic fallback between these. Reordering (or confirming the given order was already correct) is reported in `product.json`.

## Usage

The app reads `raw` and `yaml` from `config.json`, writes the `yaml` content to `config.yaml`, and passes it to MEEGFlow along with a glob reader pointing at the staged input file(s). MEEGFlow then executes each step of the pipeline in order and writes its results to `out_dir/`. Custom pipeline steps not built into MEEGFlow itself (e.g. this app's own `prepare_each_run`, `fir_filter`, `epoch_with_correctness`, ICA/evoked helpers) live under `custom_steps/` and are loaded automatically via `custom_steps_folder: custom_steps` in the pipeline YAML.

Example configuration:
```json
{
    "raw": "path/to/raw.fif",
    "yaml": "pipeline:\n  - name: concatenate_recordings\n  - name: set_montage\n    montage: standard_1020\n  - name: bandpass_filter\n    l_freq: 1.0\n    h_freq: 30.0\n  - name: reference\n    ref_channels: average\n    instance: raw\n  - name: ica\n    n_components: 15\n    method: fastica\n    find_eog: true\n    apply: true\n  - name: generate_json_report"
}
```

## Technical Details

- **Execution**: Python with the [MEEGFlow](https://github.com/BrainlifeMEEG/meegflow) pipeline engine and the shared `brainlife_utils` library
- **Data format**: MNE `.fif` format (compatible with all downstream Brainlife.io apps)
- **Pipeline steps**: Defined entirely by the `yaml` configuration parameter; available step types are provided by the MEEGFlow package plus this app's own `custom_steps/`
- **I/O backend**: `mne.io.read_raw_fif`

## Authors

- [Maximilien Chaumon](https://github.com/dnacombo), Paris Brain Institute

## Citations

We kindly ask that you cite the following articles when publishing papers and code using this app:

**brainlife.io: A decentralized and open source cloud platform to support neuroscience research**. Hayashi, S., Caron, B. A., et al. & Pestilli, F. (2023). ArXiv. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10274934/

**MEG and EEG data analysis with MNE-Python**. Gramfort A, et al. & Hämäläinen MS. (2013). Frontiers in Neuroscience, 7(267):1–13. https://doi.org/10.3389/fnins.2013.00267

## Funding Acknowledgement

brainlife.io is publicly funded and for the sustainability of the project we kindly ask that you acknowledge the following funding sources:

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB030896](https://img.shields.io/badge/NIH_NIBIB-R01EB030896-green.svg)](https://grantome.com/grant/NIH/R01-EB030896-01)

Copyright (c) 2026 MEEG Brainlife team

This project is licensed under the AGPL-3.0 License - see [license.txt](license.txt) for details.

## Citation

Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2
