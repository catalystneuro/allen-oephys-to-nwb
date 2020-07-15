from allen_oephys_to_nwb import AllenOephysNWBConverter
from pathlib import Path
import yaml
import argparse


def run_all(path_oephys_calibration, path_oephys_processed, path_oephys_raw,
            path_base_output=None, ids=None):
    """
    Sweep all files in directory and set up paths for conversion

    Parameters:
    -----------
    path_oephys : str, path
        Root path containing raw_data and processed_data directories.
    ids : list (optional)
        Runs conversion only for the specific ids (used only for testing)
    """

    path_oephys_calibration = Path(path_oephys_calibration)
    path_oephys_processed = Path(path_oephys_processed)
    path_oephys_raw = Path(path_oephys_raw)

    # Output path
    if path_base_output is None:
        path_base_output = path_oephys_calibration / 'nwb_converted'
    if not path_base_output.exists():
        path_base_output.mkdir()

    all_paths_calibration = [f for f in path_oephys_calibration.glob('*.h5') if str(f).endswith('medium.h5')]
    all_cells = []
    for p in all_paths_calibration:
        cell_id = p.name.split('_')[0]
        # Get only cell ids existing in processed directory
        aux = [f for f in path_oephys_processed.rglob(cell_id + '*.h5')]
        if len(aux) > 0:
            path_processed = aux[0]
            path_raw = [f for f in path_oephys_raw.rglob(cell_id + '*.h5')][0]
            paths_tiff = [f for f in path_oephys_raw.rglob(cell_id + '*.tif')]
            c = {
                'cell_id': cell_id,
                'group': path_raw.parent.name,
                'path_calibration': p,
                'path_raw': path_raw,
                'paths_tiff': paths_tiff,
                'path_processed': path_processed,
                'path_output': path_base_output / (cell_id + '.nwb')
            }
            all_cells.append(c)

    # Runs conversion for each cell
    if isinstance(ids, list):
        aux_list = [all_cells[int(i)] for i in ids]
    else:
        aux_list = all_cells

    for c in aux_list:
        print(f"Converting group {c['group']}, cell {c['cell_id']}...")

        # Set source paths
        source_paths = {
            'path_calibration': c['path_calibration'],
            'path_raw': c['path_raw'],
            'paths_tiff': c['paths_tiff'],
            'path_processed': c['path_processed'],
        }

        # Load metadata from YAML file
        metafile = Path.cwd() / 'metafile.yml'
        with open(metafile) as f:
            metadata = yaml.safe_load(f)

        # Instantiate converter
        converter = AllenOephysNWBConverter(
            source_paths=source_paths,
            metadata=metadata
        )

        if converter.valid:
            # Add raw optophys data - Link to external TIF files or store raw data
            converter.add_ophys_acquisition(link=True)

            # Add processed fluorescence data
            converter.add_ophys_processed()

            # Add spiking data
            converter.add_spiking_data()

            # Add Voltage traces, trace = ['raw', 'filtered']
            converter.add_ecephys_processed()

            # Add trials
            # converter.add_trials()

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
