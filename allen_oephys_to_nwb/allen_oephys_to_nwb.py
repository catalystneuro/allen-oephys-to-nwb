from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject
from pynwb.ophys import TwoPhotonSeries, OpticalChannel, Fluorescence, ImageSegmentation
from pynwb.device import Device

from .subjects_info import subjects_info

from pathlib import Path
import numpy as np
import h5py


def convert2nwb(fpath):
    """
    Convert Optophysiology and Electrophysiology data to NWB.

    Parameters:
    -----------
    fpath: path
        Path to file
    """

    fpath = Path(fpath)
    f = h5py.File(fpath, 'r')

    # Filtered membrane voltage and ephys dt
    filtered_voltage_trace = np.squeeze(f['Vmfd'])
    filtered_dt = f['dte'][0]

    # Ophys and Ephys traces should be aligned using the provided frame sync (iFrames)
    # (i.e. the matching Ephys starts at iFrames(1))
    sync_dt = f['iFrames']

    # Get subject specific information
    subject_info = subjects_info[str(int(f['aid'][0]))]

    # Initiate nwbfile
    nwbfile = NWBFile('nwbfile_name', 'ID', datetime.now(tzlocal()))
    nwbfile.pharmacology = subject_info['anesthesia']

    # Subject
    nwbfile.subject = Subject(
        subject_id=str(int(f['aid'][0])),
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
    # two_photon_series = TwoPhotonSeries(
    #     name='raw_series',
    #     imaging_plane=imaging_plane,
    #     data=,
    #     timestamps=,
    # )
    # nwbfile.add_acquisition(two_photon_series)

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
    n_rows = int(f['linesPerFrame'][0])
    n_cols = int(f['pixelsPerLine'][0][0])
    pixel_mask = []
    for pi in np.squeeze(f['pixel_list'][:]):
        row = int(pi // n_rows)
        col = int(pi % n_rows)
        pixel_mask.append([col, row, 1])
    ps.add_roi(pixel_mask=pixel_mask)

    # Fluorescene data
    fl = Fluorescence()
    ophys_module.add(fl)

    # Mean soma fluorescenceand ophys dt
    fluorescence_mean_trace = np.squeeze(f['f_cell'])
    fluorescence_dt = f['dto'][0]

    # If only one cell
    rt_region = ps.create_roi_table_region('unique cell ROI', region=[0])

    rrs = fl.create_roi_response_series(
        name='fluorescence',
        data=fluorescence_mean_trace,
        rois=rt_region,
        rate=1 / fluorescence_dt,
        starting_time=,
    )
