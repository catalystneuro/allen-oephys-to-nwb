from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class, get_base_schema
from pynwb import NWBFile


class AllenOphysInterface(BaseDataInterface):

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
                    "ophys_raw",
                    "ophys_processed",
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
        input_schema['conversion_options']['properties']['ophys_raw'] = {
            "type": "boolean",
            "default": True,
            "description": "convert raw ophys data to nwb"
        }
        input_schema['conversion_options']['properties']['ophys_processed'] = {
            "type": "boolean",
            "default": True,
            "description": "convert processed ophys data to nwb"
        }
        return input_schema

    def __init__(self, **input_args):
        super().__init__(**input_args)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()

        metadata_schema['properties']['Ophys'] = dict()

        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""
        metadata = dict()
        return metadata

    def convert_data(self, nwbfile: NWBFile, metadata_dict: dict,
                     stub_test: bool = False):
        print(nwbfile)
        # raise NotImplementedError('TODO')
