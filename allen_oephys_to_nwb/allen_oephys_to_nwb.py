from nwb_conversion_tools import NWBConverter

from .allen_ophys_interface import AllenOphysInterface
from .allen_ecephys_interface import AllenEcephysInterface

import numpy as np
import h5py


class AllenOephysNWBConverter(NWBConverter):

    # Modular data interfaces
    data_interface_classes = {
        'AllenEcephysInterface': AllenEcephysInterface,
        'AllenOphysInterface': AllenOphysInterface,
    }

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
