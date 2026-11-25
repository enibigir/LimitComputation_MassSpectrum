"""Paths of the inputs of CreateDatacards.py, read from one JSON file (default: cfg/paths.json).

CreateDatacards.py and the driver take --paths FILE to read another one ($LIMIT_PATHS too).
Relative paths are taken from the directory of this repository, so the default file works when
the repository sits inside TupleAnalysis, next to massSpectrum_bckgPrediction. $VARIABLES and ~
are expanded.

    import paths
    P = paths.load()              # or paths.load(options.paths)
    P.bkg_dir, P.bkg_dataset, P.bkg_sample_type
    P.signal_file("gluino", 2000)
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(REPO, "cfg", "paths.json")


class PathsError(Exception):
    pass


def resolve(p):
    """Absolute path: $VARIABLES and ~ expanded, relative paths taken from the repository."""
    p = os.path.expanduser(os.path.expandvars(p))
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(REPO, p))


class Paths(object):
    def __init__(self, doc, source):
        self.source = source

        def need(d, key, kind, where=""):
            if key not in d:
                raise PathsError("{}: '{}{}' missing".format(source, where, key))
            if not isinstance(d[key], kind):
                raise PathsError("{}: '{}{}' must be a {}".format(source, where, key, kind.__name__))
            return d[key]

        bkg = need(doc, "background", dict)
        self.bkg_dir = resolve(need(bkg, "dir", str, "background."))
        self.bkg_dataset = need(bkg, "dataset", str, "background.")
        self.bkg_sample_type = need(bkg, "sampleType", str, "background.")

        self.signals = {}
        for name, s in need(doc, "signals", dict).items():
            if not isinstance(s, dict):
                raise PathsError("{}: signals.{} must be an object".format(source, name))
            pattern = need(s, "pattern", str, "signals.{}.".format(name))
            if "{mass}" not in pattern:
                raise PathsError("{}: signals.{}.pattern must hold {{mass}}".format(source, name))
            self.signals[name] = (resolve(need(s, "dir", str, "signals.{}.".format(name))), pattern)

    def bkg_input_dir(self, region, optionlabel, eta_dir):
        """<dir>/<sampleType>__<region>_<optionlabel>/<eta>/, as filed by LaunchBkgPred.py."""
        return os.path.join(self.bkg_dir, "{}__{}_{}".format(self.bkg_sample_type, region, optionlabel),
                            eta_dir)

    def signal_file(self, signal, mass):
        if signal not in self.signals:
            sys.exit("paths: {}: no signal '{}' (signals: {})".format(
                self.source, signal, ", ".join(sorted(self.signals))))
        d, pattern = self.signals[signal]
        return os.path.join(d, pattern.format(mass=mass))


def load(path=None):
    """Read the paths file; exits with a message if it cannot be used."""
    path = path or os.environ.get("LIMIT_PATHS") or DEFAULT
    try:
        with open(path) as f:
            doc = json.load(f)
        return Paths(doc, path)
    except (OSError, IOError, ValueError, PathsError) as e:
        sys.exit("paths: {}".format(e))
