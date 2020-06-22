from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject
from pynwb.ophys import TwoPhotonSeries, OpticalChannel, Fluorescence, ImageSegmentation
from pynwb.device import Device
from hdmf.data_utils import DataChunkIterator

from .subjects_info import subjects_info

from pathlib import Path
from libtiff import TIFF
import numpy as np
import h5py


def convert2nwb(path_raw, path_tiff, path_processed, path_output):
    """
    Convert Optophysiology and Electrophysiology data to NWB.

    Parameters:
    -----------
    path_raw: str, path
        Path to H5 file containing raw electrophys data
    path_tiff: str, path
        Path to TIF file containing raw ophys data
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

    # Read processeddata
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
