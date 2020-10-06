from allen_oephys_to_nwb import AllenOephysNWBConverter
from pathlib import Path
import json


source_data_path = Path('.').resolve() / 'source_example.json'
with open(source_data_path, 'r') as inp:
    input_data = json.load(inp)

print('Input schema:')
print(AllenOephysNWBConverter.get_input_schema())
print('')

a = AllenOephysNWBConverter(input_data)

print('Interface input args:')
print(a.data_interface_objects['AllenEcephys'].input_args)
print(a.data_interface_objects['AllenOphys'].input_args)
print('')

metadata_schema = a.get_metadata_schema()

print('Metadata schema:')
print(metadata_schema)
