from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
import pynwb


class AllenEcephysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        input_schema = {
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

    def convert_data(self):
        raise NotImplementedError('TODO')
