from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_schema_from_hdmf_class
from nwb_conversion_tools.json_schema_utils import get_base_schema
import pynwb
from pynwb import NWBFile
from pathlib import Path
import importlib.resources as pkg_resources
import numpy as np
import h5py
import json
from . import schema
from .utils import get_basic_metadata


class AllenEcephysInterface(BaseDataInterface):

    @classmethod
    def get_source_schema(cls):
        with pkg_resources.open_text(schema, 'source_schema_ecephys.json') as f:
            source_schema = json.load(f)
        return source_schema

    def get_metadata_schema(self):
        metadata_schema = super().get_metadata_schema()
        metadata_schema['properties']['Ecephys'] = get_base_schema(tag='Ecephys')
        metadata_schema['properties']['Ecephys']['properties']['Device'] = get_schema_from_hdmf_class(pynwb.device.Device)
        metadata_schema['properties']['Ecephys']['properties']['ElectrodeGroup'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectrodeGroup)
        metadata_schema['properties']['Ecephys']['properties']['ElectricalSeries_raw'] = get_schema_from_hdmf_class(pynwb.ecephys.ElectricalSeries)

        return metadata_schema

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible."""

        metadata = get_basic_metadata(source_data=self.source_data)
        metadata['Ecephys'] = dict(
            Device=dict(name='MultiClamp 700B'),
            ElectrodeGroup=dict(
                name='ElectrodeGroup',
                description='2-p targeted cell-attached',
                location='primary visual cortex - layer 2/3',
                device='MultiClamp 700B'
            )
        )

        # Raw electrical series metadata
        path_raw = Path(self.source_data["path_raw"])
        with h5py.File(path_raw, 'r') as f:
            ecephys_rate = 1 / np.array(f['dte'])
        metadata['Ecephys']['ElectricalSeries_raw'] = {
            'name': 'ElectricalSeries_raw',
            'description': 'ADDME',
            'rate': float(ecephys_rate)
        }

        return metadata

    def run_conversion(self, nwbfile: NWBFile, metadata: dict,
                       stub_test: bool = False, add_ecephys_raw: bool = False,
                       add_ecephys_processed: bool = False, add_ecephys_spiking: bool = False):
        """
        Options:
        add_ecephys_raw : boolean
        add_ecephys_processed : boolean
        add_ecephys_spiking : boolean
        """
        if add_ecephys_raw or add_ecephys_processed:
            # ElectrodeGroups
            self._create_electrode_groups(
                nwbfile=nwbfile,
                metadata_ecephys=metadata['Ecephys']
            )
            # Electrodes
            self._create_electrodes(nwbfile=nwbfile)

        if add_ecephys_raw:
            # Raw ecephys
            self._create_ecephys_raw(
                nwbfile=nwbfile,
                metadata_ecephys=metadata['Ecephys']
            )

        if add_ecephys_processed:
            # Processed ecephys
            self._create_ecephys_processed(
                nwbfile=nwbfile,
                metadata_ecephys=metadata['Ecephys']
            )

        if add_ecephys_spiking:
            # Spiking data ecephys
            self._create_ecephys_spiking(
                nwbfile=nwbfile,
                metadata_ecephys=metadata['Ecephys']
            )

    def _create_electrode_groups(self, nwbfile: NWBFile, metadata_ecephys: dict):
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
            print(f'Adding ElectrodesGroup: {key}...')
            metadata_elec_group = metadata_ecephys[key]
            eg_name = metadata_elec_group['name']
            # Tests if ElectrodeGroup already exists
            aux = [i.name == eg_name for i in nwbfile.children]
            if any(aux):
                print(eg_name + ' already exists in current NWBFile.')
            else:
                device_name = metadata_elec_group['device']
                if device_name in nwbfile.devices:
                    device = nwbfile.devices[device_name]
                else:
                    print('Device ', device_name, ' for ElectrodeGroup ', eg_name, ' does not exist.')
                    print('Make sure ', device_name, ' is defined in metadata.')

                eg_description = metadata_elec_group['description']
                eg_location = metadata_elec_group['location']
                nwbfile.create_electrode_group(
                    name=eg_name,
                    location=eg_location,
                    device=device,
                    description=eg_description
                )

    def _create_electrodes(self, nwbfile):
        """Add electrode"""
        print('Adding electrode...')
        electrode_group = list(nwbfile.electrode_groups.values())[0]
        nwbfile.add_electrode(
            id=0,
            x=np.nan, y=np.nan, z=np.nan,
            imp=np.nan,
            location='location',
            filtering='none',
            group=electrode_group
        )

    def _create_ecephys_raw(self, nwbfile: NWBFile, metadata_ecephys: dict):
        """Add raw membrane voltage data"""
        print('Converting raw ecephys data...')
        path_raw = self.input_args["path_raw"]
        with h5py.File(path_raw, 'r') as f:
            electrode_table_region = nwbfile.create_electrode_table_region(
                region=[0],
                description='electrode'
            )

            trace_data = np.squeeze(f['Voltage'])
            trace_name = metadata_ecephys['ElectricalSeries_raw']['name']
            description = metadata_ecephys['ElectricalSeries_raw']['description']
            ecephys_rate = metadata_ecephys['ElectricalSeries_raw']['rate']
            electrical_series = pynwb.ecephys.ElectricalSeries(
                name=trace_name,
                description=description,
                data=trace_data,
                electrodes=electrode_table_region,
                starting_time=0.,
                rate=float(ecephys_rate),
            )
            nwbfile.add_acquisition(electrical_series)

    def _create_ecephys_processed(self, nwbfile: NWBFile, metadata_ecephys: dict):
        """Add processed membrane voltage data"""
        raise NotImplementedError('TODO')
        print('Converting processed ecephys data...')

    def _create_ecephys_spiking(self, nwbfile: NWBFile, metadata_ecephys: dict):
        """Add spiking data"""
        raise NotImplementedError('TODO')
        print('Converting spiking data...')
