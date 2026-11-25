"""Inputs of CreateDatacards.py and luminosity of the plots, read from one JSON file
(default: cfg/paths.json).

CreateDatacards.py, the plotting scripts and the driver take --paths FILE to read another one
($LIMIT_PATHS too).
Relative paths are taken from the directory of this repository, so the default file works when
the repository sits inside TupleAnalysis, next to massSpectrum_bckgPrediction. $VARIABLES and ~
are expanded.

    import paths
    P = paths.load()              # or paths.load(options.paths)
    P.bkg_dir, P.bkg_dataset, P.bkg_sample_type
    P.signal_file("gluino", 2000)
    P.lumi_text_mpl(), P.lumi_text_root()   # "109 fb$^{-1}$ (13.6 TeV)", "109 fb^{-1} (13.6 TeV)"
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

        # Luminosity of the plot labels: optional, the 2024 dataset by default
        lumi = doc.get("luminosity", {})
        if not isinstance(lumi, dict):
            raise PathsError("{}: 'luminosity' must be an object".format(source))
        self.lumi_fb = lumi.get("value_fb", 109)
        self.energy = lumi.get("energy", "13.6 TeV")
        if isinstance(self.lumi_fb, bool) or not isinstance(self.lumi_fb, (int, float)) or self.lumi_fb <= 0:
            raise PathsError("{}: luminosity.value_fb must be a positive number".format(source))
        if not isinstance(self.energy, str):
            raise PathsError("{}: luminosity.energy must be a string".format(source))

    def bkg_input_dir(self, region, optionlabel, eta_dir):
        """<dir>/<sampleType>__<region>_<optionlabel>/<eta>/, as filed by LaunchBkgPred.py."""
        return os.path.join(self.bkg_dir, "{}__{}_{}".format(self.bkg_sample_type, region, optionlabel),
                            eta_dir)

    def lumi_text_mpl(self):
        """Luminosity label for matplotlib (mathtext)."""
        return r"{:g} fb$^{{-1}}$ ({})".format(self.lumi_fb, self.energy)

    def lumi_text_root(self):
        """Luminosity label for ROOT (TLatex)."""
        return "{:g} fb^{{-1}} ({})".format(self.lumi_fb, self.energy)

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
