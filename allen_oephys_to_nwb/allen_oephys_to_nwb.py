from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject
from pynwb.ophys import TwoPhotonSeries, OpticalChannel, Fluorescence, ImageSegmentation
from pynwb.device import Device
from hdmf.data_utils import DataChunkIterator
from nwb_conversion_tools import NWBConverter

from .subjects_info import subjects_info

from pathlib import Path
from libtiff import TIFF
import PIL as pil
import numpy as np
import h5py


class AllenOephysNWBConverter(NWBConverter):

    def __init__(self, source_paths, metadata=None, nwbfile=None):
        # Set up metadata with info from files
        with h5py.File(source_paths['path_processed'], 'r') as f:
            session_identifier = str(int(f['tid'][0]))
            animal_id = str(int(f['aid'][0]))
            subject_info = subjects_info[animal_id]

        # File metadata
        meta_nwbfile = {
            'session_description': 'session description',
            'identifier': session_identifier,
            'session_start_time': datetime.now(tzlocal()),
            'pharmacology': subject_info['anesthesia'],
        }
        if metadata is None:
            metadata = {}
            metadata['NWBFile'] = meta_nwbfile
        else:
            metadata['NWBFile'].update(meta_nwbfile)

        # Subject metadata
        meta_subject = {
            'subject_id': animal_id,
            'genotype': subject_info['line'],
            'age': subject_info['age']
        }
        if 'Subject' in metadata:
            metadata['Subject'].update(meta_subject)
        else:
            metadata['Subject'] = meta_subject

        super().__init__(metadata=metadata, nwbfile=nwbfile, source_paths=source_paths)

    def create_electrodes_ecephys(self):
        """Add electrode"""
        raise NotImplementedError('TODO')

    def add_ecephys_acquisition(self, meta_acquisition):
        """Add raw / filtered membrane voltage data"""
        raise NotImplementedError('TODO')

    def _get_imaging_plane(self):
        """Add new / return existing Imaging Plane"""
        meta_imgplane = self.metadata['Ophys']['ImagingPlane'][0]
        if meta_imgplane['name'] in self.nwbfile.imaging_planes:
            imaging_plane = self.nwbfile.imaging_planes[meta_imgplane['name']]
        else:
            with h5py.File(self.source_paths['path_processed'], 'r') as f:
                if 'depth' in f:
                    description = 'high zoom'
                else:
                    description = 'low zoom'
                animal_id = str(int(f['aid'][0]))
                subject_info = subjects_info[animal_id]
                indicator = subject_info['indicator']
                imaging_rate = 1 / f['dto'][0]

                # Create Imaging Plane
                meta_optch = meta_imgplane['optical_channel'][0]
                optical_channel = OpticalChannel(**meta_optch)
                imaging_plane = self.nwbfile.create_imaging_plane(
                    name='imaging_plane',
                    optical_channel=optical_channel,
                    description=description,
                    device=self.nwbfile.devices[meta_imgplane['device']],
                    excitation_lambda=meta_imgplane['excitation_lambda'],
                    indicator=indicator,
                    location=meta_imgplane['location'],
                    imaging_rate=imaging_rate,
                )

        return imaging_plane

    def add_ophys_processed(self):
        """Add Fluorescence data"""
        imaging_plane = self._get_imaging_plane()
        with h5py.File(self.source_paths['path_processed'], 'r') as f:
            # Stores segmented data
            ophys_module = self.nwbfile.create_processing_module(
                name='ophys',
                description='contains optical physiology processed data'
            )

            meta_imgseg = self.metadata['Ophys']['ImageSegmentation']
            img_seg = ImageSegmentation(name=meta_imgseg['name'])
            ophys_module.add(img_seg)

            meta_planeseg = meta_imgseg['plane_segmentations'][0]
            plane_segmentation = img_seg.create_plane_segmentation(
                name=meta_planeseg['name'],
                description=meta_planeseg['description'],
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
            meta_fluorescence = self.metadata['Ophys']['Fluorescence']
            fl = Fluorescence(name=meta_fluorescence['name'])
            ophys_module.add(fl)

            fluorescence_mean_trace = np.squeeze(f['f_cell'])
            rt_region = plane_segmentation.create_roi_table_region(
                description='unique cell ROI',
                region=[0]
            )

            imaging_rate = 1 / f['dto'][0]
            fl.create_roi_response_series(
                name=meta_fluorescence['roi_response_series'][0]['name'],
                data=fluorescence_mean_trace,
                rois=rt_region,
                rate=imaging_rate,
                starting_time=0.,
                unit='no unit'
            )

    def add_ophys_acquisition(self, link=True):
        """Add raw ophys data from tiff files"""

        # Iteratively read tiff ophys data
        def tiff_iterator(paths_tiff):
            for tf in paths_tiff:
                tif = TIFF.open(tf)
                for image in tif.iter_images():
                    yield image
                tif.close()

        with h5py.File(self.source_paths['path_processed'], 'r') as f:
            imaging_rate = 1 / f['dto'][0]
        imaging_plane = self._get_imaging_plane()

        # Link to raw data files
        if link:
            starting_frames = [0]
            for i, tf in enumerate(self.source_paths['paths_tiff'][0:-1]):
                n_frames = pil.Image.open(tf).n_frames
                starting_frames.append(n_frames + starting_frames[i])
            two_photon_series = TwoPhotonSeries(
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

    def add_spiking(self, meta_processed):
        """Add spiking data"""
        raise NotImplementedError('TODO')


def convert2nwb(path_raw, path_tiff, path_processed, path_output):
    """
    Convert Optophysiology and Electrophysiology data to NWB.

    Parameters:
    -----------
    path_raw: str, path
        Path to H5 file containing raw electrophys data
    path_tiff: list of str, path
        List with paths to TIF files containing raw ophys data
    path_processed: str, path
        Path to H5 file containing processed electrophys and ophys data
    path_output: str, path
        Path to output NWB file
    """

    # Iteratively read tiff ophys data
    def tiff_iterator(path_tiff):
        tif = TIFF.open(path_tiff)
        for image in tif.iter_images():
            yield image
        tif.close()

    # Read processeddata
    path_raw = Path(path_raw)
    f_raw = h5py.File(path_raw, 'r')

    # Read processed high zoom data
    path_processed = Path(path_processed)
    f_processed = h5py.File(path_processed, 'r')

    # Get subject specific information
    subject_info = subjects_info[str(int(f_processed['aid'][0]))]

    # Initiate nwbfile
    nwbfile = NWBFile('nwbfile_name', 'ID', datetime.now(tzlocal()))
    nwbfile.pharmacology = subject_info['anesthesia']

    # Subject
    nwbfile.subject = Subject(
        subject_id=str(int(f_processed['aid'][0])),
        genotype=subject_info['line'],
        age=subject_info['age']
    )

    # Add Device
    device = Device('ophys_device_1')
    nwbfile.add_device(device)

    # Create Imaging Plane
    optical_channel = OpticalChannel('optical_channel', 'description', 500.)
    imaging_plane = nwbfile.create_imaging_plane(
        name='imaging_plane',
        optical_channel=optical_channel,
        description='description',
        device=device,
        excitation_lambda=600.,
        indicator='GCaMP6s',
        location='primary visual cortex - layer 2/3',
        imaging_rate=300.,
    )

    # Stores raw data
    raw_data_iterator = DataChunkIterator(data=tiff_iterator(path_tiff))
    two_photon_series = TwoPhotonSeries(
        name='raw_ophys',
        imaging_plane=imaging_plane,
        data=raw_data_iterator,
        starting_time=0.,
        rate=10.,
        unit='no unit'
    )
    nwbfile.add_acquisition(two_photon_series)

    # Electrophysiology

    # Raw membrane voltage trace and dt



    # Filtered membrane voltage and ephys dt
    filtered_voltage_trace = np.squeeze(f_processed['Vmfd'])
    filtered_dt = f_processed['dte'][0]

    # Ophys and Ephys traces should be aligned using the provided frame sync (iFrames)
    # (i.e. the matching Ephys starts at iFrames(1))
    sync_dt = f_processed['iFrames']

    # Stores segmented data
    ophys_module = nwbfile.create_processing_module('ophys', 'contains optical physiology processed data')
    img_seg = ImageSegmentation()
    ophys_module.add(img_seg)

    ps = img_seg.create_plane_segmentation(
        name='plane_segmentation',
        description='description',
        imaging_plane=imaging_plane,
    )

    # ROIs
    n_rows = int(f_processed['linesPerFrame'][0])
    n_cols = int(f_processed['pixelsPerLine'][0][0])
    pixel_mask = []
    for pi in np.squeeze(f_processed['pixel_list'][:]):
        row = int(pi // n_rows)
        col = int(pi % n_rows)
        pixel_mask.append([col, row, 1])
    ps.add_roi(pixel_mask=pixel_mask)

    # Fluorescene data
    fl = Fluorescence()
    ophys_module.add(fl)

    # Mean soma fluorescenceand ophys dt
    fluorescence_mean_trace = np.squeeze(f_processed['f_cell'])
    fluorescence_dt = f_processed['dto'][0]

    # If only one cell
    rt_region = ps.create_roi_table_region('unique cell ROI', region=[0])

    fl.create_roi_response_series(
        name='fluorescence',
        data=fluorescence_mean_trace,
        rois=rt_region,
        rate=1 / fluorescence_dt,
        starting_time=0.,
        unit='no unit'
    )

    # Write to nwb file
    print('Saving data to file...')
    with NWBHDF5IO(str(path_output), 'w') as io:
        io.write(nwbfile)
        print('File saved: ', str(path_output))

    # Test read
    with NWBHDF5IO(str(path_output), 'r') as io:
        nwbfile2 = io.read()
        print('File load test passed')
