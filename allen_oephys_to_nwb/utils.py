from datetime import datetime
from pathlib import Path
import numpy as np
import json
import uuid
import h5py


def get_basic_metadata(source_data):
    """Get basic metadata info from files"""

    if 'path_subjects_info' in source_data:
        subjects_info_path = source_data['path_subjects_info']
        if Path(subjects_info_path).is_file():
            with open(subjects_info_path, 'r') as inp:
                all_subjects_info = json.load(inp)

    subject_info = {
        'subject_id': None,
        'line': None,
        'age': None,
        'anesthesia': None
    }

    session_identifier = str(uuid.uuid4())
    if 'path_processed' in source_data and Path(source_data['path_processed']).is_file():
        with h5py.File(source_data['path_processed'], 'r') as f:
            session_identifier = str(int(f['tid'][0]))
            if np.isnan(f['aid'][0]):
                print(f"File {source_data['path_processed']} does not have 'aid' key. Skipping it...")
            else:
                subject_id = str(int(f['aid'][0]))
                subject_info = all_subjects_info[subject_id]
                subject_info['subject_id'] = subject_id

    # initiate metadata
    metadata = dict(
        NWBFile=dict(
            session_description='session description',
            identifier=session_identifier,
            session_start_time=datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'),
            institution='Allen Institute for Brain Science',
            pharmacology=subject_info['anesthesia'],
        ),
        Subject=dict(
            subject_id=subject_info['subject_id'],
            genotype=subject_info['line'],
            age=subject_info['age']
        )
    )

    return metadata
