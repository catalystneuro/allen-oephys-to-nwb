from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject
from pynwb.ophys import TwoPhotonSeries, OpticalChannel, Fluorescence, ImageSegmentation
from pynwb.ecephys import ElectricalSeries
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

    def _create_electrodes_ecephys(self):
        """Add electrode"""
        electrode_group = list(self.nwbfile.electrode_groups.values())[0]
        self.nwbfile.add_electrode(
            id=0,
            x=np.nan, y=np.nan, z=np.nan,
            imp=np.nan,
            location='location',
            filtering='none',
            group=electrode_group
        )

    def add_ecephys_acquisition(self, trace=['raw', 'filtered']):
        """Add raw / filtered membrane voltage data"""

        self._create_electrodes_ecephys()
        with h5py.File(self.source_paths['path_processed'], 'r') as f:
            electrode_table_region = self.nwbfile.create_electrode_table_region(
                region=[0],
                description='electrode'
            )
            ecephys_rate = 1 / f['dte'][0]

            for tr in trace:
                if tr == 'raw':
                    trace_data = np.squeeze(f['Vm'])
                    trace_name = 'raw_membrane_voltage'
                    description = 'raw voltage trace'
                if tr == 'filtered':
                    trace_data = np.squeeze(f['Vmfd'])
                    trace_name = 'filtered_membrane_voltage'
                    description = 'voltage trace filtered between 250 Hz and 5 kHz'
                electrical_series = ElectricalSeries(
                    name=trace_name,
                    description=description,
                    data=trace_data,
                    electrodes=electrode_table_region,
                    starting_time=0.,
                    rate=ecephys_rate,
                )
                self.nwbfile.add_acquisition(electrical_series)

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

    def add_spiking_data(self):
        """Add spiking data"""
        with h5py.File(self.source_paths['path_processed'], 'r') as f:
            spike_times = np.where(f['spk'][0])[0] * f['dte'][0]
            self.nwbfile.add_unit(spike_times=spike_times)

    def add_trials(self):
        """Add trials data"""
        with h5py.File(self.source_paths['path_processed'], 'r') as f:
            if ('iStimOn' in f) and ('iStimOff' in f):
                stim_on = f['iStimOn'][:][0]
                stim_off = f['iStimOff'][:][0]
                trial_times = np.hstack((stim_on.reshape(-1, 1), stim_off.reshape((-1, 1)))).reshape(-1) * f['dte'][0]
                trial_times = np.append(trial_times, trial_times[-1] + 0.25)
                sweep_order = np.squeeze(f['sweep_order'][:])
                sweep_table = f['sweep_table'][:].T.reshape((-1, 4))
                sweep_table = np.vstack((np.array([[np.nan, np.nan, np.nan, np.nan]]), sweep_table))

                self.nwbfile.add_trial_column(name='orientation', description='description')
                self.nwbfile.add_trial_column(name='phase', description='description')
                self.nwbfile.add_trial_column(name='spatial_frequency', description='description')
                self.nwbfile.add_trial_column(name='contrast', description='description')

                for i, stim in enumerate(sweep_order):
                    stim = int(stim + 1)
                    self.nwbfile.add_trial(
                        start_time=trial_times[i],
                        stop_time=trial_times[i + 1],
                        orientation=sweep_table[stim, 0],
                        phase=sweep_table[stim, 1],
                        spatial_frequency=sweep_table[stim, 2],
                        contrast=sweep_table[stim, 3]
                    )
            else:
                print('This file does not have stimulation data!')
