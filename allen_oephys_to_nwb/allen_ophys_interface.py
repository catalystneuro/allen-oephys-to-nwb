from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from nwb_conversion_tools.json_schema_utils import get_base_schema
from pynwb import NWBFile
import pynwb

import importlib.resources as pkg_resources
from libtiff import TIFF
from PIL import Image as pImage
import json
import h5py

from . import schema
from .utils import get_basic_metadata


class AllenOphysInterface(BaseDataInterface):

    @classmethod
    def get_source_schema(cls):
        with pkg_resources.open_text(schema, 'source_schema_ophys.json') as f:
            source_schema = json.load(f)
        return source_schema

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema['properties']['Ophys'] = get_base_schema(tag='Ophys')
        metadata_schema['properties']['Ophys']['properties']['Device'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ophys']['properties']['ImagingPlane'] = get_schema_from_hdmf_class(pynwb.ophys.ImagingPlane)
        metadata_schema['properties']['Ophys']['properties']['TwoPhotonSeries'] = get_schema_from_hdmf_class(pynwb.ophys.TwoPhotonSeries)
        metadata_schema['properties']['Ophys']['properties']['Fluorescence'] = get_schema_from_hdmf_class(pynwb.ophys.Fluorescence)
        # metadata_schema['properties']['Ophys']['properties']['ImageSegmentation'] = get_schema_from_hdmf_class(pynwb.ophys.ImageSegmentation)

        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""

        metadata = get_basic_metadata(source_data=self.source_data)
        metadata['Ophys'] = dict(
            Device=dict(name='Bruker 2-p microscope'),
            Fluorescence=dict(name='Fluorescence'),
            ImagingPlane=dict(
                name='ImagingPlane',
                description='ADDME',
                indicator='ADDME',
                device='Bruker 2-p microscope',
                excitation_lambda=920,
                location='primary visual cortex - layer 2/3',
                imaging_rate=0.0,
                # optical_channel=[
                #     dict(
                #         name='optical_channel',
                #         description='2P Optical Channel',
                #         emission_lambda=510
                #     )
                # ]
            ),
            TwoPhotonSeries=dict(
                name='TwoPhotonSeries_green',
                imaging_plane='ImagingPlane'
            )
        )

        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict,
                       stub_test: bool = False, add_ophys_raw: bool = False,
                       add_ophys_processed: bool = False):
        """
        Options:
        add_ophys_raw : boolean
        add_ophys_processed : boolean
        """
        return
        # print(nwbfile)
        # raise NotImplementedError('TODO')

    def _get_imaging_plane(self, nwbfile: NWBFile, metadata_imgplane: dict):
        """Add new / return existing Imaging Plane"""

        # If ImagingPlane already exists
        if metadata_imgplane['name'] in nwbfile.imaging_planes:
            return nwbfile.imaging_planes[metadata_imgplane['name']]

        # Create OpticalChannel
        metadata_optch = metadata_imgplane['optical_channel'][0]
        optical_channel = pynwb.ophys.OpticalChannel(**metadata_optch)

        # Create ImagingPlane
        imaging_plane = nwbfile.create_imaging_plane(
            name=metadata_imgplane['name'],
            optical_channel=optical_channel,
            description=metadata_imgplane['description'],
            device=self.nwbfile.devices[metadata_imgplane['device']],
            excitation_lambda=metadata_imgplane['excitation_lambda'],
            indicator=metadata_imgplane['indicator'],
            location=metadata_imgplane['location'],
            imaging_rate=metadata_imgplane['imaging_rate'],
        )

        return imaging_plane

    def _create_ophys_raw(self, nwbfile: NWBFile, metadata_ophys: dict):
        """Add raw ophys data from tiff files"""

        # Iteratively read tiff ophys data
        def tiff_iterator(paths_tiff):
            for tf in paths_tiff:
                tif = TIFF.open(tf)
                for image in tif.iter_images():
                    yield image
                tif.close()

        imaging_plane = self._get_imaging_plane(
            nwbfile=nwbfile,
            metadata_imgplane=metadata_ophys['ImagingPlane']
        )

        metadata_twops = metadata_ophys['TwoPhotonSeries']

        # Link to raw data files
        if self.input_args['raw_ophys_link']:
            starting_frames = [0]
            for i, tf in enumerate(self.source_paths['paths_tiff'][0:-1]):
                n_frames = pImage.open(tf).n_frames
                starting_frames.append(n_frames + starting_frames[i])
            two_photon_series = pynwb.ophys.TwoPhotonSeries(
                name='raw_ophys',
                imaging_plane=imaging_plane,
                format='tiff',
                external_file=self.source_paths['paths_tiff'],
                starting_frame=starting_frames,
                starting_time=0.,
                rate=imaging_rate,
                unit='no unit'
            )
        # Store raw data
        else:
            raw_data_iterator = DataChunkIterator(data=tiff_iterator(self.source_paths['paths_tiff']))
            two_photon_series = TwoPhotonSeries(
                name='raw_ophys',
                imaging_plane=imaging_plane,
                data=raw_data_iterator,
                starting_time=0.,
                rate=imaging_rate,
                unit='no unit'
            )
        self.nwbfile.add_acquisition(two_photon_series)
