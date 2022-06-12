import os
from pathlib import Path

folders_to_check = [
    "eval_dedicated_pre",
    "eval_zooming_1_pre",
    "eval_zooming_100_pre",
    "eval_uniform_pre",
    "eval_caida_pre",
    "eval_tofino_pre",
    "eval_comparison_pre",
]


class PrecomputedInputsDirError(Exception):
    pass


def check_precomputed_inputs_dir(path_to_dir, checks=folders_to_check):
    """Checks if directory exists and all precomputed directories are there.

    Args:
        path_to_dir (_type_): _description_
        checks (_type_, optional): _description_. Defaults to folders_to_check.
    """

    # checks if directory exists
    if not os.path.isdir(path_to_dir):
        raise PrecomputedInputsDirError(
            "Inputs dir {} does not exist".format(path_to_dir))

    root_path = Path(path_to_dir)
    # checks if all directories exist
    missing_dirs = []
    for subdir in checks:
        _subdir = root_path / subdir
        if not root_path in _subdir.parent:
            missing_dirs.append(_subdir)

    # raise error
    if missing_dirs:
        raise PrecomputedInputsDirError(
            "Some precomputed inputs are missing: {}".format(
                ", ".join(missing_dirs)))

    return True
