# allen_oephys_to_nwb

NWB conversion scripts for [Huang, L., et al](https://www.biorxiv.org/content/10.1101/788802v2.full).

# Install
```
$ pip install git+https://github.com/catalystneuro/allen-to-nwb
```

# Usage

```python
from allen_oephys_to_nwb import AllenOephysNWBConverter
from pynwb import NWBHDF5IO
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import yaml

# Set source paths
base_name = 'Emx1-f_highzoom/102956'
path_raw = Path('../raw_data/' + base_name + '.h5').absolute()
paths_tiff = [Path('../raw_data/' + base_name + '_2.tif').absolute()]
path_processed = Path('../processed_data/' + base_name + '_processed.h5').absolute()
source_paths = {
    'path_raw': path_raw,
    'paths_tiff': paths_tiff,
    'path_processed': path_processed,
}

# Load metadata from YAML file
metafile = Path('metafile.yml')
with open(metafile) as f:
   metadata = yaml.safe_load(f)

# Instantiate converter
converter = AllenOephysNWBConverter(
    source_paths=source_paths,
    metadata=metadata
)

# Add processed fluorescence data
converter.add_ophys_processed()

# Add raw optophys data - Link to external TIF files or store raw data
converter.add_ophys_acquisition(link=True)

# Add spiking data
converter.add_spiking_data()

# Add Voltage traces, trace = ['raw', 'filtered']
converter.add_ecephys_acquisition(trace=['raw', 'filtered'])

# Add trials
converter.add_trials()

# Save to file
path_output = 'oephys_example.nwb'
converter.save(to_path=path_output, read_check=True)
```
