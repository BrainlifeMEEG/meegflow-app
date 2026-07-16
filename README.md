# app-meegflow

## Description

This app runs a configurable [MEEGFlow](https://github.com/BrainlifeMEEG/meegflow) preprocessing pipeline on MEG/EEG data. MEEGFlow executes a sequence of processing steps (e.g. concatenation, montage assignment, filtering, referencing, ICA, report generation) described by a YAML pipeline specification supplied through `config.json`. This allows a single app to run a full, user-defined preprocessing chain in one step.

## Inputs

- **raw**: MNE raw data file in `.fif` format (must be named `raw.fif` in its containing directory, since it is located via a glob pattern)

## Outputs

- **out_dir/**: Outputs produced by the MEEGFlow pipeline, as determined by the configured pipeline steps
- **product.json**: Metadata describing pipeline execution status and results

## Configuration Parameters

### Required

- `raw`: Path to the input MNE raw data file (`.fif` format, named `raw.fif`)
- `yaml`: A YAML-formatted string defining the MEEGFlow pipeline to execute. Each entry in the `pipeline` list specifies a processing step by `name` and its parameters.

## Usage

The app reads `raw` and `yaml` from `config.json`, writes the `yaml` content to `config.yaml`, and passes it to MEEGFlow along with a glob reader pointing at the directory containing the input `raw.fif` file. MEEGFlow then executes each step of the pipeline in order and writes its results to `out_dir/`.

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
- **Pipeline steps**: Defined entirely by the `yaml` configuration parameter; available step types are provided by the MEEGFlow package
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

#### MIT Copyright (c) 2026 brainlife.io The University of Texas at Austin and Indiana University

## Citation

Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2
