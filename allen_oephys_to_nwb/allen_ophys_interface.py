from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class, get_base_schema
from pynwb import NWBFile
import pynwb
import importlib.resources as pkg_resources
import json
from . import schema
from .utils import get_basic_metadata


class AllenOphysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        with pkg_resources.open_text(schema, 'source_schema_ophys.json') as f:
            input_schema = json.load(f)
        return input_schema['properties']

    def __init__(self, **input_args):
        super().__init__(**input_args)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()

        metadata_schema['properties']['Ophys'] = get_base_schema(tag='Ophys')
        metadata_schema['properties']['Ophys']['properties']['Device'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ophys']['properties']['ImagingPlane'] = get_schema_from_hdmf_class(pynwb.ophys.ImagingPlane)
        metadata_schema['properties']['Ophys']['properties']['TwoPhotonSeries'] = get_schema_from_hdmf_class(pynwb.ophys.TwoPhotonSeries)
        metadata_schema['properties']['Ophys']['properties']['Fluorescence'] = get_schema_from_hdmf_class(pynwb.ophys.Fluorescence)
        # metadata_schema['properties']['Ophys']['properties']['ImageSegmentation'] = get_schema_from_hdmf_class(pynwb.ophys.ImageSegmentation)

        return metadata_schema

    def get_metadata(self, metadata):
        """Auto-fill as much of the metadata as possible."""

        if not metadata:
            metadata = get_basic_metadata(input_args=self.input_args)

        metadata['Ophys'] = dict(
            Device=dict(name='Bruker 2-p microscope'),
            Fluorescence=dict(name='Fluorescence'),
            ImagingPlane=dict(
                name='ImagingPlane',
                device='Bruker 2-p microscope',
                excitation_lambda=920,
                location='primary visual cortex - layer 2/3',
                # optical_channel=[
                #     dict(
                #         description='2P Optical Channel',
                #         emission_lambda=510,
                #         name='optical_channel'
                #     )
                # ]
            ),
            TwoPhotonSeries=dict(
                name='TwoPhotonSeries_green',
                imaging_plane='ImagingPlane'
            )
        )

        return metadata

    def convert_data(self, nwbfile: NWBFile, metadata_dict: dict,
                     stub_test: bool = False):
        print(nwbfile)
        # raise NotImplementedError('TODO')
