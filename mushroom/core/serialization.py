"""Versioned NumPy archives with JSON metadata and no pickle payloads."""
import json
import numpy as np


def save_npz(path, kind, data, array_keys):
    """Write named arrays and scalar JSON metadata to a compressed archive."""
    arrays = {k: np.asarray(v) for k, v in data.items() if k in array_keys and v is not None}
    if any(a.dtype.hasobject for a in arrays.values()):
        raise ValueError("Object arrays are not allowed")
    meta = {k: v for k, v in data.items() if k not in array_keys}
    meta.update(format="mushroom", format_version=1, kind=kind)
    arrays["__meta__"] = np.array(json.dumps(meta))
    with open(path, "wb") as handle:
        np.savez_compressed(handle, **arrays)


def load_npz(path, kind):
    """Read a version-1 archive using only NumPy, rejecting other kinds."""
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
