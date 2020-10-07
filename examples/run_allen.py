from allen_oephys_to_nwb import AllenOephysNWBConverter
from pathlib import Path
import json
import pprint


pp = pprint.PrettyPrinter(depth=6)

source_data_path = Path(__file__).parent.resolve() / 'source_example.json'
with open(source_data_path, 'r') as inp:
    input_data = json.load(inp)

a = AllenOephysNWBConverter(input_data)

metadata_schema = a.get_metadata_schema()
metadata_dict = a.get_metadata()

nwbfile = a.run_conversion(metadata_dict, save_to_file=False)

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
