from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class, get_base_schema
from pynwb import NWBFile
import json


class AllenOphysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        with open('source_schema.json') as f:
            input_schema = json.load(f)
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
