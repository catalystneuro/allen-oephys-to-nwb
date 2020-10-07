from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
import pynwb
from pynwb import NWBFile
from datetime import datetime
import numpy as np
import h5py
import json


class AllenEcephysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        input_schema = {
            'source_data': {
                "title": "Source Files",
                "type": "object",
                "required": [
                    'path_calibration',
                    'path_raw',
                    'paths_tiff',
                    'path_processed',
                    'subjects_info'
                ],
                "properties": {}
            },
            'conversion_options': {
                "title": "Conversion options",
                "type": "object",
                "required": [
                    "ecephys_spiking",
                    "ecephys_processed"
                ],
                "properties": {}
            },
        }
        # Source files
        input_schema['source_data']['properties']['path_calibration'] = {
            "type": "string",
            "format": "file",
            "description": "path to calibration data file"
        }
        input_schema['source_data']['properties']['path_raw'] = {
            "type": "string",
            "format": "file",
            "description": "path to raw data file"
        }
        input_schema['source_data']['properties']['path_tiff'] = {
            "type": "string",
            "format": "file",
            "description": "path to tiff data file"
        }
        input_schema['source_data']['properties']['path_processed'] = {
            "type": "string",
            "format": "file",
            "description": "path to processed data file"
        }
        input_schema['source_data']['properties']['subjects_info'] = {
            "type": "string",
            "format": "file",
            "description": "path to subjects info data file"
        }
        # Conversion options
        input_schema['conversion_options']['properties']['ecephys_spiking'] = {
            "type": "boolean",
            "default": True,
            "description": "convert spiking data to nwb"
        }
        input_schema['conversion_options']['properties']['ecephys_processed'] = {
            "type": "boolean",
            "default": True,
            "description": "convert ecephys processed data to nwb"
        }
        return input_schema

    def __init__(self, **input_args):
        super().__init__(**input_args)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()
        metadata_schema['properties']['Ecephys'] = dict()
        metadata_schema['properties']['Ecephys']['Device'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ecephys']['ElectrodeGroup'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectrodeGroup)
        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""
        metadata = dict()

        # Get metadata info from files
        subjects_info_path = self.input_args['source_data']['subjects_info']
        with open(subjects_info_path, 'r') as inp:
            subjects_info = json.load(inp)

        with h5py.File(self.input_args['source_data']['path_processed'], 'r') as f:
            session_identifier = str(int(f['tid'][0]))
            if np.isnan(f['aid'][0]):
                print(f"File {self.input_args['source_data']['path_processed']} does not have 'aid' key. Skipping it...")
                subject_info = {
                    'subject_id': '',
                    'genotype': '',
                    'age': '',
                    'anesthesia': ''
                }
            else:
                subject_id = str(int(f['aid'][0]))
                subject_info = subjects_info[subject_id]
                subject_info['subject_id'] = subject_id

        # File metadata
        metadata['NWBFile'] = {
            'session_description': 'session description',
            'identifier': session_identifier,
            'session_start_time': datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'),
            'pharmacology': subject_info['anesthesia'],
        }

        # Subject metadata
        metadata['Subject'] = {
            'subject_id': subject_info['subject_id'],
            'genotype': subject_info['line'],
            'age': subject_info['age']
        }

        return metadata

    def convert_data(self, nwbfile: NWBFile, metadata_dict: dict,
                     stub_test: bool = False):
        print(nwbfile)
        # raise NotImplementedError('TODO')
