from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
from . import schema
import pynwb
from pynwb import NWBFile
from datetime import datetime
from pathlib import Path
import importlib.resources as pkg_resources
import numpy as np
import h5py
import json
import uuid


class AllenEcephysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        with pkg_resources.open_text(schema, 'source_schema.json') as f:
            input_schema = json.load(f)
        return input_schema['properties']

    def __init__(self, **input_args):
        super().__init__(**input_args)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()
        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')
        metadata_schema['properties']['Ecephys']['properties']['Device'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ecephys']['properties']['ElectrodeGroup'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectrodeGroup)
        metadata_schema['properties']['Ecephys']['properties']['ElectricalSeries_raw'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectricalSeries)
        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""
        metadata = dict()

        # Get metadata info from files
        subjects_info_path = self.input_args['source_data']['path_subjects_info']
        if Path(subjects_info_path).is_file():
            with open(subjects_info_path, 'r') as inp:
                subjects_info = json.load(inp)

        subject_info = {
            'subject_id': '',
            'line': '',
            'age': '',
            'anesthesia': ''
        }

        session_identifier = str(uuid.uuid4())
        if 'path_processed' in self.input_args['source_data']:
            with h5py.File(self.input_args['source_data']['path_processed'], 'r') as f:
                session_identifier = str(int(f['tid'][0]))
                if np.isnan(f['aid'][0]):
                    print(f"File {self.input_args['source_data']['path_processed']} does not have 'aid' key. Skipping it...")
                else:
                    subject_id = str(int(f['aid'][0]))
                    subject_info = subjects_info[subject_id]
                    subject_info['subject_id'] = subject_id

        # initiate metadata
        metadata = dict(
            NWBFile=dict(
                session_description='session description',
                identifier=session_identifier,
                session_start_time=datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'),
                pharmacology=subject_info['anesthesia'],
            ),
            Subject=dict(
                subject_id=subject_info['subject_id'],
                genotype=subject_info['line'],
                age=subject_info['age']
            ),
            Ecephys=dict(
                Device=dict(name='Device_ecephys'),
                ElectrodeGroup=dict(
                    name='ElectrodeGroup',
                    description='no description',
                    location='unknown',
                    device='Device_ecephys'
                )
            )
        )

        # Raw electrical series metadata
        path_raw = Path(self.input_args["source_data"]["path_raw"])
        with h5py.File(path_raw, 'r') as f:
            ecephys_rate = 1 / np.array(f['dte'])
        metadata['Ecephys']['ElectricalSeries_raw'] = {
            'name': 'ElectricalSeries_raw',
            'rate': ecephys_rate
        }

        return metadata

    def convert_data(self, nwbfile: NWBFile, metadata_dict: dict,
                     stub_test: bool = False):
        self.nwbfile = nwbfile

        # ElectrodeGroups
        self._create_electrode_groups(metadata_dict['Ecephys'])
        # Electrodes
        self._create_electrodes()
        # Raw ecephys
        self._create_raw_ecephys(metadata_dict['Ecephys'])

    def _create_electrode_groups(self, metadata_ecephys):
        """
        Use metadata to create ElectrodeGroup object(s) in the NWBFile

        Parameters
        ----------
        metadata_ecephys : dict
            Dict with key:value pairs for the Ecephys group from where this
            ElectrodeGroup belongs. This should contain keys for required groups
            such as 'Device', 'ElectrodeGroup', etc.
        """
        for key in [k for k in metadata_ecephys if 'ElectrodeGroup' in k]:
            metadata_elec_group = metadata_ecephys[key]
            eg_name = metadata_elec_group['name']
            # Tests if ElectrodeGroup already exists
            aux = [i.name == eg_name for i in self.nwbfile.children]
            if any(aux):
                print(eg_name + ' already exists in current NWBFile.')
            else:
                device_name = metadata_elec_group['device']
                if device_name in self.nwbfile.devices:
                    device = self.nwbfile.devices[device_name]
                else:
                    print('Device ', device_name, ' for ElectrodeGroup ', eg_name, ' does not exist.')
                    print('Make sure ', device_name, ' is defined in metadata.')

                eg_description = metadata_elec_group['description']
                eg_location = metadata_elec_group['location']
                self.nwbfile.create_electrode_group(
                    name=eg_name,
                    location=eg_location,
                    device=device,
                    description=eg_description
                )

    def _create_electrodes(self):
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

    def _create_raw_ecephys(self, metadata_ecephys):
        """Add raw membrane voltage data"""
        self._create_electrodes_ecephys()
        path_raw = self.input_args["source_data"]["path_raw"]
        with h5py.File(path_raw, 'r') as f:
            electrode_table_region = self.nwbfile.create_electrode_table_region(
                region=[0],
                description='electrode'
            )

            trace_data = np.squeeze(f['Voltage'])
            trace_name = metadata_ecephys['ElectricalSeries_raw']['trace_name']
            description = metadata_ecephys['ElectricalSeries_raw']['description']
            ecephys_rate = metadata_ecephys['ElectricalSeries_raw']['rate']
            electrical_series = pynwb.ecephys.ElectricalSeries(
                name=trace_name,
                description=description,
                data=trace_data,
                electrodes=electrode_table_region,
                starting_time=0.,
                rate=ecephys_rate,
            )
            self.nwbfile.add_acquisition(electrical_series)
