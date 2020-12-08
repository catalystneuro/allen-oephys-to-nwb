from pathlib import Path, PureWindowsPath


def get_fix_path(path):
    if '\\' in path:
        win_path = PureWindowsPath(path)
        path = Path(win_path)
        if str(path).startswith('\\'):
            path = str(path).replace('\\', '', 1)
            path = Path(path)
        return path
    else:
        return Path(path)