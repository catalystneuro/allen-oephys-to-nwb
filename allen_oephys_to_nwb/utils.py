from datetime import datetime
from pathlib import Path
import numpy as np
import json
import uuid
import h5py
import pytz
import random
import string


def get_basic_metadata(source_data):
    """Get basic metadata info from files"""

    if 'path_subjects_info' in source_data:
        subjects_info_path = source_data['path_subjects_info']
        if Path(subjects_info_path).is_file():
            with open(subjects_info_path, 'r') as inp:
                all_subjects_info = json.load(inp)

    subject_info = {
        'subject_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)),
        'line': None,
        'age': None,
        'anesthesia': None
    }

    session_identifier = str(uuid.uuid4())
    fname = None
    if 'path_ecephys_processed' in source_data and Path(source_data['path_ecephys_processed']).is_file():
        fname = source_data['path_ecephys_processed']
    elif 'path_ophys_processed' in source_data and Path(source_data['path_ophys_processed']).is_file():
        fname = source_data['path_ophys_processed']
    if fname:
        with h5py.File(fname, 'r') as f:
            session_identifier = str(int(f['tid'][0]))
            if np.isnan(f['aid'][0]):
                print(f"File {fname} does not have 'aid' key. Skipping it...")
            else:
                subject_id = str(int(f['aid'][0]))
                subject_info = all_subjects_info[subject_id]
                subject_info['subject_id'] = subject_id

    # initiate metadata
    session_start_time = datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    session_start_time_tzaware = pytz.timezone('EST').localize(session_start_time)
    metadata = dict(
        NWBFile=dict(
            session_description='session description',
            identifier=session_identifier,
            session_start_time=session_start_time_tzaware.isoformat(),
            institution='Allen Institute for Brain Science',
            pharmacology=subject_info['anesthesia'],
        ),
        Subject=dict(
            subject_id=subject_info['subject_id'],
            genotype=subject_info['line'],
            age=str(subject_info['age'])
        )
    )

    return metadata
