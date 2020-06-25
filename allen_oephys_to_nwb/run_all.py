from allen_oephys_to_nwb import AllenOephysNWBConverter
from pathlib import Path
import yaml
import argparse


def run_all(path_oephys, ids=None):
    """
    Sweep all files in directory and set up paths for conversion

    Parameters:
    -----------
    path_oephys : str, path
        Root path containing raw_data and processed_data directories.
    ids : list (optional)
        Runs conversion only for the specific ids (used only for testing)
    """

    path_oephys = Path(path_oephys)
    path_base_output = path_oephys / 'nwb_converted'

    all_raw_paths = list((path_oephys / 'raw_data').rglob('*.h5'))
    all_processed_paths = list((path_oephys / 'processed_data').rglob('*.h5'))
    all_cells = []
    for p in all_raw_paths:
        path_output = path_base_output / p.parent.name
        if not path_output.exists():
            path_output.mkdir()
        c = {
            'id': p.stem,
            'group': p.parent.name,
            'path_raw': p,
            'paths_tiff': list(p.parent.glob(p.stem + '*.tif')),
            'path_processed': [pp for pp in all_processed_paths if p.stem in str(pp)][0],
            'path_output': path_output / (p.stem + '.nwb')
        }
        all_cells.append(c)

    # Runs conversion for each cell
    if isinstance(ids, list):
        aux_list = [all_cells[int(i)] for i in ids]
    else:
        aux_list = all_cells

    for c in aux_list:
        print(f"Converting group {c['group']}, cell {c['id']}...")

        # Set source paths
        source_paths = {
            'path_raw': c['path_raw'],
            'paths_tiff': c['paths_tiff'],
            'path_processed': c['path_processed'],
        }

        # Load metadata from YAML file
        metafile = 'metafile.yml'
        with open(metafile) as f:
            metadata = yaml.safe_load(f)

        # Instantiate converter
        converter = AllenOephysNWBConverter(
            source_paths=source_paths,
            metadata=metadata
        )

        if converter.valid:
            # Add processed fluorescence data
            converter.add_ophys_processed()

            # Add raw optophys data - Link to external TIF files or store raw data
            converter.add_ophys_acquisition(link=True)

            # Add spiking data
            converter.add_spiking_data()

            # Add Voltage traces, trace = ['raw', 'filtered']
            converter.add_ecephys_acquisition(trace=['raw', 'filtered'])

            # Add trials
            converter.add_trials()

            # Save to file
            path_output = str(c['path_output'])
            converter.save(to_path=path_output, read_check=True)


if __name__ == '__main__':
    import sys

    parser = argparse.ArgumentParser("Convert OEphys to NWB.")

    parser.add_argument(
        "path_oephys",
        help="The path to the root directory holding raw and processed data"
    )
    parser.add_argument(
        "--ids",
        default=None,
        help="List of ids to convert",
    )

    if not sys.argv[1:]:
        args = parser.parse_args(["--help"])
    else:
        args = parser.parse_args()

    path_oephys = Path(args.path_oephys)
    if args.ids is not None:
        ids = [b.strip() for b in args.ids.split(',')]
    else:
        ids = None

    run_all(path_oephys=path_oephys, ids=ids)
