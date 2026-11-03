"""Versioned NumPy archives with JSON metadata and no pickle payloads."""
import json

import numpy as np


def save_npz(path, kind, data, array_keys):
    """Write named arrays and scalar JSON metadata to a compressed archive.

    Args:
        path (path-like): Destination archive, preserving the supplied filename.
        kind (str): Object type stored in the metadata.
        data (dict): Arrays and JSON-serializable metadata. Units and array shapes
            follow the object type; None-valued arrays are omitted.
        array_keys (sequence of str): Keys stored as named NumPy arrays; remaining
            fields are encoded in the scalar Unicode __meta__ array.

    Returns:
        None: Writes a version-1 npz readable with NumPy alone and no pickle.

    Raises:
        ValueError: If an array has object dtype.
        TypeError: If metadata is not JSON-serializable.
        OSError: If the archive cannot be written.
    """
    arrays = {k: np.asarray(v) for k, v in data.items() if k in array_keys and v is not None}
    if any(a.dtype.hasobject for a in arrays.values()):
        raise ValueError("Object arrays are not allowed")
    meta = {k: v for k, v in data.items() if k not in array_keys}
    meta.update(format="mushroom", format_version=1, kind=kind)
    arrays["__meta__"] = np.array(json.dumps(meta))
    with open(path, "wb") as handle:
        np.savez_compressed(handle, **arrays)


def load_npz(path, kind):
    """Read a version-1 archive using only NumPy, rejecting other kinds.

    Args:
        path (path-like): Source npz archive with a scalar JSON __meta__ entry.
        kind (str): Required object type.

    Returns:
        dict: Named arrays and decoded metadata, preserving stored units and shapes.

    Raises:
        ValueError: If format, version or kind is unsupported, or arrays require pickle.
        KeyError: If required __meta__ fields are absent.
        OSError: If the archive cannot be read.
    """
    with np.load(path, allow_pickle=False) as archive:
        meta = json.loads(archive["__meta__"].item())
        actual = meta.get("kind")
        if (meta.get("format") != "mushroom" or meta.get("format_version") != 1
                or actual != kind):
            raise ValueError("Unsupported archive: kind={!r}, format={!r}, version={!r}; expected {} v1".format(
                actual, meta.get("format"), meta.get("format_version"), kind))
        for key in ("kind", "format", "format_version"):
            meta.pop(key)
        meta.update({k: archive[k] for k in archive.files if k != "__meta__"})
    return meta
