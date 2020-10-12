from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
import pynwb
from pynwb import NWBFile
from datetime import datetime
import numpy as np
import h5py
import json


class AllenEcephysInterface(BaseDataInterface):

    @classmethod
    def get_input_schema(cls):
        input_schema = {
            'source_data': {
                "title": "Source Files",
                "type": "object",
                "required": [
                    # 'path_calibration',
                    'path_raw',
                    # 'paths_tiff',
                    # 'path_processed',
                    # 'subjects_info'
                ],
                "properties": {}
            },
            'conversion_options': {
                "title": "Conversion options",
                "type": "object",
                "required": [
                    "ecephys_spiking",
                    "ecephys_processed"
                ],
                "properties": {}
            },
        }
        # Source files
        input_schema['source_data']['properties']['path_raw'] = {
            "type": "string",
            "format": "file",
            "description": "path to raw data file"
        }
        # input_schema['source_data']['properties']['path_calibration'] = {
        #     "type": "string",
        #     "format": "file",
        #     "description": "path to calibration data file"
        # }
        # input_schema['source_data']['properties']['path_tiff'] = {
        #     "type": "string",
        #     "format": "file",
        #     "description": "path to tiff data file"
        # }
        # input_schema['source_data']['properties']['path_processed'] = {
        #     "type": "string",
        #     "format": "file",
        #     "description": "path to processed data file"
        # }
        # input_schema['source_data']['properties']['subjects_info'] = {
        #     "type": "string",
        #     "format": "file",
        #     "description": "path to subjects info data file"
        # }

        # Conversion options
        input_schema['conversion_options']['properties']['ecephys_spiking'] = {
            "type": "boolean",
            "default": True,
            "description": "convert spiking data to nwb"
        }
        input_schema['conversion_options']['properties']['ecephys_processed'] = {
            "type": "boolean",
            "default": True,
            "description": "convert ecephys processed data to nwb"
        }
        return input_schema

    def __init__(self, **input_args):
        super().__init__(**input_args)

    def get_metadata_schema(self):
        metadata_schema = get_base_schema()
        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')
        metadata_schema['properties']['Ecephys']['properties']['Device_1'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ecephys']['properties']['Device_2'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ecephys']['properties']['ElectrodeGroup'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectrodeGroup)
        metadata_schema['properties']['Ecephys']['properties']['ElectricalSeries_raw'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectricalSeries)
        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""
        metadata = dict()

        return metadata

        # Get metadata info from files
        subjects_info_path = self.input_args['source_data']['subjects_info']
        with open(subjects_info_path, 'r') as inp:
            subjects_info = json.load(inp)

        with h5py.File(self.input_args['source_data']['path_processed'], 'r') as f:
            session_identifier = str(int(f['tid'][0]))
            if np.isnan(f['aid'][0]):
                print(f"File {self.input_args['source_data']['path_processed']} does not have 'aid' key. Skipping it...")
                subject_info = {
                    'subject_id': '',
                    'line': '',
                    'age': '',
                    'anesthesia': ''
                }
            else:
                subject_id = str(int(f['aid'][0]))
                subject_info = subjects_info[subject_id]
                subject_info['subject_id'] = subject_id

        # File metadata
        metadata['NWBFile'] = {
            'session_description': 'session description',
            'identifier': session_identifier,
            'session_start_time': datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'),
            'pharmacology': subject_info['anesthesia'],
        }

        # Subject metadata
        metadata['Subject'] = {
            'subject_id': subject_info['subject_id'],
            'genotype': subject_info['line'],
            'age': subject_info['age']
        }

        # Ecephys metadata
        metadata['Ecephys'] = dict()
        metadata['Ecephys']['Device'] = {
            'name': 'Device_ecephys'
        }

        metadata['Ecephys']['ElectrodeGroup'] = [
            {
                'name': 'ElectrodeGroup',
                'description': 'no description',
                'location': '',
                'device': 'Device_ecephys'
            }
        ]

        # Raw electrical series metadata
        path_raw = self.input_args["source_data"]["path_raw"]
        with h5py.File(path_raw, 'r') as f:
            ecephys_rate = 1 / np.array(f['dte'])
        metadata['Ecephys']['ElectricalSeries_raw'] = {
            'name': 'ElectricalSeries_raw',
            'rate': ecephys_rate
        }

        return metadata

    def convert_data(self, nwbfile: NWBFile, metadata_dict: dict,
                     stub_test: bool = False):
        print(nwbfile)
        # raise NotImplementedError('TODO')

    def create_electrode_groups(self, metadata_ecephys):
        """
        Use metadata to create ElectrodeGroup object(s) in the NWBFile

        Parameters
        ----------
        metadata_ecephys : dict
            Dict with key:value pairs for the Ecephys group from where this
            ElectrodeGroup belongs. This should contain keys for required groups
            such as 'Device', 'ElectrodeGroup', etc.
        """
        for metadata_elec_group in metadata_ecephys['ElectrodeGroup']:
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

    def add_ecephys_raw(self):
        """Add raw membrane voltage data"""
        self._create_electrodes_ecephys()
        path_raw = self.input_args["source_data"]["path_raw"]
        with h5py.File(path_raw, 'r') as f:
            electrode_table_region = self.nwbfile.create_electrode_table_region(
                region=[0],
                description='electrode'
            )
            ecephys_rate = 1 / np.array(f['dte'])

            trace_data = np.squeeze(f['Voltage'])
            trace_name = 'raw_ecephys'
            description = 'Raw voltage trace'
            electrical_series = pynwb.ecephys.ElectricalSeries(
                name=trace_name,
                description=description,
                data=trace_data,
                electrodes=electrode_table_region,
                starting_time=0.,
                rate=ecephys_rate,
            )
            self.nwbfile.add_acquisition(electrical_series)
