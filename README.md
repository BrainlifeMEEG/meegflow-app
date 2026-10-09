# MEEGFlow Preprocessing Pipeline

[![Run on Brainlife.io](https://img.shields.io/badge/Brainlife-bl.app.928-blue.svg)](https://doi.org/10.25663/brainlife.app.928)

## Description

This app runs a configurable [MEEGFlow](https://github.com/BrainlifeMEEG/meegflow) preprocessing pipeline on MEG/EEG data. MEEGFlow executes a sequence of processing steps (e.g. concatenation, montage assignment, filtering, referencing, ICA, report generation) described by a YAML pipeline specification supplied through `config.json`. This allows a single app to run a full, user-defined preprocessing chain in one step.

The app generates:
- Preprocessed raw and/or epoched data, and averaged evoked data, depending on which steps the configured pipeline runs
- An interactive MNE Report (when the pipeline runs `generate_html_report`)
- Quick-look preview figures (PSD for a raw output, averaged ERP for an epochs output), embedded in `product.json`
- `product.json` Brainlife.io metadata describing pipeline execution status and results

## Inputs

- **`raw`** (`neuro/meeg/mne/raw`): One or more MNE raw data files in `.fif` format (each named `raw.fif` in its own containing directory, since each is located via a glob pattern) (required). When more than one is given, they're concatenated into a single recording before the pipeline runs — see `run_order` below for how their order is determined.

  When the input dataset(s) carry brainlife's `subject`/`session`/`run` metadata, the app feeds it into meegflow itself (not just `product.json`): meegflow's report title and its BIDS-style output filenames use the real subject/session instead of defaulting to `None`, and the full identity (including run number(s)) is recorded in the report's preprocessing-steps list and in `product.json`. Concatenating raw files with conflicting `subject` metadata is treated as a likely input-selection mistake and fails the task before running anything; conflicting `session` metadata only produces a warning (the first session found is used).

## Outputs

Which of these are produced depends entirely on which steps the configured pipeline YAML runs;
each is only written if the corresponding step is present.

- **`out_raw/raw.fif`** (`neuro/meeg/mne/raw`): Preprocessed raw data, written when the pipeline runs `save_clean_instance` with `instance: raw`
- **`out_epo/meg-epo.fif`** (`neuro/meeg/mne/epochs`): Preprocessed epochs, written when the pipeline runs `save_clean_instance` with `instance: epochs`
- **`out_evoked/*.fif`** (`neuro/meeg/mne/evoked`): Averaged evoked data, written by the `average_by_event_type`/`average_condition_group` custom steps (see `custom_steps/` in the source), if used
- **`out_report/report.html`** (`report/html`): Interactive MNE Report, written when the pipeline runs `generate_html_report`
- **`product.json`**: Metadata describing pipeline execution status and results

## Configuration Parameters

| key | type | default | description |
|---|---|---|---|
| `yaml` | string | `"pipeline:\n  - name: concatenate_recordings ...\n  - name: save_clean_instance\n    instance: raw\n  - name: generate_html_report"` | A YAML-formatted string defining the MEEGFlow pipeline to execute. Each entry in the `pipeline` list specifies a processing step by `name` and its parameters. |
| `run_order` | enum (`as-is`, `sort_by_meas_date`, `sort_by_tags`) | `"as-is"` | How to order multiple `raw` inputs before concatenation. `as-is` uses the given input order untouched. `sort_by_meas_date` sorts by each file's own recording start time, and fails clearly if any input is missing one. `sort_by_tags` sorts by each file's brainlife dataset tags (best-effort — tags aren't guaranteed unique or sortable), and fails clearly if any input has no tags. There is no automatic fallback between these. Reordering (or confirming the given order was already correct) is reported in `product.json`. |

## Usage

The app reads `raw` and `yaml` from `config.json`, writes the `yaml` content to `config.yaml`, and passes it to MEEGFlow along with a glob reader pointing at the staged input file(s). MEEGFlow then executes each step of the pipeline in order and writes its results to `out_dir/`. Custom pipeline steps not built into MEEGFlow itself (e.g. this app's own `prepare_each_run`, `fir_filter`, `epoch_with_correctness`, ICA/evoked helpers, `set_recording_metadata`) live under `custom_steps/` and are always available — the app wires up `custom_steps_folder: custom_steps` itself, so the pipeline YAML doesn't need to declare it. `set_recording_metadata` is prepended to every pipeline automatically (it seeds meegflow's `data['subject']`/`data['session']` from brainlife's own dataset metadata, as described under `raw` above) and doesn't need to be listed in the YAML either.

### Running on Brainlife.io

1. Select your MEG/EEG raw `.fif` dataset(s) as the `raw` input (multiple inputs are concatenated).
2. Write the MEEGFlow pipeline steps as a YAML string in `yaml`.
3. If multiple `raw` inputs are given, optionally set `run_order` to control concatenation order.
4. Submit the process.
5. Review the preview figures, HTML report and other outputs in the output viewer.

### Local Testing

```bash
# Edit config.json to point "raw" at a real raw .fif file and "yaml" at a pipeline, then:
python main.py
```

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

- Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2
- Gramfort, A. et al. MEG and EEG data analysis with MNE-Python. Front. Neurosci. 7, 267 (2013). https://doi.org/10.3389/fnins.2013.00267

## Funding Acknowledgement

brainlife.io is publicly funded and for the sustainability of the project we kindly ask that you acknowledge the following funding sources:

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)
[![NIH-NIBIB-R01EB030896](https://img.shields.io/badge/NIH_NIBIB-R01EB030896-green.svg)](https://grantome.com/grant/NIH/R01-EB030896-01)

## License

Copyright (c) 2026 MEEG Brainlife team. Licensed under AGPL-3.0, see [license.txt](license.txt).
