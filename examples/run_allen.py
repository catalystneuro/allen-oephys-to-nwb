from allen_oephys_to_nwb import AllenOephysNWBConverter
from pathlib import Path
import pprint


pp = pprint.PrettyPrinter(depth=6)

source_path = Path(r'D:\Dropbox\oephys_calibration_dataset_from_the_allen_institute')
input_data = {
    "source_data": {
        "path_calibration": source_path / "calibration.h5",
        "path_raw": source_path / "raw.h5",
        "path_tiff": source_path / "image.tif",
        "path_processed": source_path / "oephys_dataset_original/processed_data/Cux2-f_highzoom/103703_processed.h5",
        "subjects_info": source_path / "subjects_info.json"
    },
    "conversion_options": {
        "ophys_raw": True,
        "ophys_processed": True,
        "ecephys_spiking": True,
        "ecephys_processed": True
    }
}

a = AllenOephysNWBConverter(input_data)

metadata_schema = a.get_metadata_schema()
metadata_dict = a.get_metadata()

print('Metadata:')
pp.pprint(metadata_dict)

# nwbfile = a.run_conversion(metadata_dict, save_to_file=False)

aux = False
if aux:
    print('Input schema:')
    pp.pprint(AllenOephysNWBConverter.get_input_schema())
    print('')

    print('Interface input args:')
    pp.pprint(a.data_interface_objects['AllenEcephys'].input_args)
    pp.pprint(a.data_interface_objects['AllenOphys'].input_args)
    print('')

    print('Metadata schema:')
    pp.pprint(metadata_schema)
