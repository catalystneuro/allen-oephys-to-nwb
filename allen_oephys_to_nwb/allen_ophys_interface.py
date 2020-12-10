from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from nwb_conversion_tools.json_schema_utils import get_base_schema
from pynwb import NWBFile
import pynwb
from hdmf.data_utils import DataChunkIterator

import importlib.resources as pkg_resources
from libtiff import TIFF
from PIL import Image as pImage
import numpy as np
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
        metadata_schema['properties']['Ophys']['properties']['TwoPhotonSeries_green'] = get_schema_from_hdmf_class(pynwb.ophys.TwoPhotonSeries)
        metadata_schema['properties']['Ophys']['properties']['Fluorescence'] = get_schema_from_hdmf_class(pynwb.ophys.Fluorescence)

        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""

        metadata = get_basic_metadata(source_data=self.source_data)
        metadata['Ophys'] = dict(
            Device=dict(name='Bruker 2-p microscope'),
            Fluorescence=dict(
                name='Fluorescence',
                roi_response_series=[
                    dict(name='roi_response_series')
                ]
            ),
            ImagingPlane=dict(
                name='ImagingPlane',
                description='ADDME',
                indicator='ADDME',
                device='Bruker 2-p microscope',
                excitation_lambda=920,
                location='primary visual cortex - layer 2/3',
                imaging_rate=0.0,
                optical_channel=[
                    dict(
                        name='optical_channel',
                        description='2P Optical Channel',
                        emission_lambda=510.0
                    )
                ]
            ),
            TwoPhotonSeries_green=dict(
                name='TwoPhotonSeries_green',
                imaging_plane='ImagingPlane'
            )
        )

        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict,
                       stub_test: bool = False, add_ophys_processed: bool = False,
                       add_ophys_raw: bool = False, link_ophys_raw: bool = False):
        """
        Options:
        add_ophys_raw : boolean
        add_ophys_processed : boolean
        link_ophys_raw : boolean
        """
        if add_ophys_raw or add_ophys_processed:
            # Device
            nwbfile.create_device(**metadata['Ophys']['Device'])

        # Processed ophys series
        if add_ophys_processed:
            self._create_ophys_processed(
                nwbfile=nwbfile,
                metadata=metadata
            )

        # Raw ophys series
        if add_ophys_raw:
            self._create_ophys_raw(
                nwbfile=nwbfile,
                metadata=metadata,
                link_ophys_raw=link_ophys_raw
            )

    def _get_imaging_plane(self, nwbfile: NWBFile, metadata_imgplane: dict):
        """Add new / return existing Imaging Plane"""
        # If ImagingPlane already exists
        if metadata_imgplane['name'] in nwbfile.imaging_planes:
            return nwbfile.imaging_planes[metadata_imgplane['name']]

        # Device
        device_name = metadata_imgplane['device']
        if device_name in nwbfile.devices:
            device = nwbfile.devices[device_name]
        else:
            raise ValueError(f"Device {device_name} for ImagingPlane {metadata_imgplane['name']}"
                             "does not exist. Make sure {device_name} is defined in metadata.")

        # Create OpticalChannel
        metadata_optch = metadata_imgplane['optical_channel'][0]
        optical_channel = pynwb.ophys.OpticalChannel(
            name=metadata_optch['name'],
            description=metadata_optch['description'],
            emission_lambda=float(metadata_optch['emission_lambda']),
        )

        # Create ImagingPlane
        imaging_plane = nwbfile.create_imaging_plane(
            name=metadata_imgplane['name'],
            optical_channel=optical_channel,
            description=metadata_imgplane['description'],
            device=device,
            excitation_lambda=float(metadata_imgplane['excitation_lambda']),
            indicator=metadata_imgplane['indicator'],
            location=metadata_imgplane['location'],
            imaging_rate=float(metadata_imgplane['imaging_rate']),
            origin_coords_unit='meters'
        )

        return imaging_plane

    def _create_ophys_processed(self, nwbfile: NWBFile, metadata: dict):
        """Add Fluorescence data"""
        print('Converting processed ophys data...')
        imaging_plane = self._get_imaging_plane(
            nwbfile=nwbfile,
            metadata_imgplane=metadata['Ophys']['ImagingPlane']
        )
        with h5py.File(self.source_data['path_ophys_processed'], 'r') as f:
            # Stores segmented data
            ophys_module = nwbfile.create_processing_module(
                name='ophys',
                description='contains optical physiology processed data'
            )

            # Image Segmentation
            img_seg = pynwb.ophys.ImageSegmentation(name='ImageSegmentation')
            ophys_module.add(img_seg)

            # Plane Segmentation
            plane_segmentation = img_seg.create_plane_segmentation(
                name='PlaneSegmentation',
                description='no description',
                imaging_plane=imaging_plane,
            )

            # ROIs
            n_rows = int(f['linesPerFrame'][0])
            n_cols = int(f['pixelsPerLine'][0][0])
            pixel_mask = []
            for pi in np.squeeze(f['pixel_list'][:]):
                row = int(pi // n_rows)
                col = int(pi % n_rows)
                pixel_mask.append([col, row, 1])
            plane_segmentation.add_roi(pixel_mask=pixel_mask)

            # Fluorescene data
            meta_fluorescence = metadata['Ophys']['Fluorescence']
            fl = pynwb.ophys.Fluorescence(name=meta_fluorescence['name'])
            ophys_module.add(fl)

            with h5py.File(self.source_data['path_ophys_processed'], 'r') as fc:
                # fluorescence_mean_trace = np.squeeze(fc['dff'])
                fluorescence_mean_trace = np.squeeze(fc['f_cell'])
                rt_region = plane_segmentation.create_roi_table_region(
                    description='unique cell ROI',
                    region=[0]
                )

                imaging_rate = 1 / fc['dto'][0]
                fl.create_roi_response_series(
                    name=meta_fluorescence['roi_response_series'][0]['name'],
                    data=fluorescence_mean_trace,
                    rois=rt_region,
                    rate=imaging_rate,
                    starting_time=0.,
                    unit='no unit'
                )

    def _create_ophys_raw(self, nwbfile: NWBFile, metadata: dict,
                          link_ophys_raw: bool):
        """Add raw ophys data from tiff files"""
        print('Converting raw ophys data...')

        # Iteratively read tiff ophys data
        def tiff_iterator(paths_tiff):
            for tf in paths_tiff:
                tif = TIFF.open(tf)
                for image in tif.iter_images():
                    yield image
                tif.close()

        # Get imaging rate
        with h5py.File(self.source_data['path_ophys_processed'], 'r') as f:
            imaging_rate = 1 / f['dto'][0]

        # Imaging Plane
        imaging_plane = self._get_imaging_plane(
            nwbfile=nwbfile,
            metadata_imgplane=metadata['Ophys']['ImagingPlane']
        )

        metadata_twops = metadata['Ophys']['TwoPhotonSeries_green']

        # Link to raw data files
        if link_ophys_raw:
            starting_frames = [0]
            for i, tf in enumerate(self.source_data['path_tiff_green_channel'][0:-1]):
                n_frames = pImage.open(tf).n_frames
                starting_frames.append(n_frames + starting_frames[i])
            two_photon_series = pynwb.ophys.TwoPhotonSeries(
                name=metadata_twops['name'],
                imaging_plane=imaging_plane,
                format='tiff',
                external_file=self.source_data['paths_tiff'],
                starting_frame=starting_frames,
                starting_time=0.,
                rate=imaging_rate,
                unit='no unit'
            )
        # Store raw data
        else:
            raw_data_iterator = DataChunkIterator(
                data=tiff_iterator([self.source_data['path_tiff_green_channel']])
            )
            two_photon_series = pynwb.ophys.TwoPhotonSeries(
                name=metadata_twops['name'],
                imaging_plane=imaging_plane,
                data=raw_data_iterator,
                starting_time=0.,
                rate=imaging_rate,
                unit='no unit'
            )
        nwbfile.add_acquisition(two_photon_series)
