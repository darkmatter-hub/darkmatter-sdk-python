"""The package metadata must not name a person.

setup.py carried a real name in `author` and pointed `Source` at a personal
GitHub account. Every release from 0.1.0 to 1.4.5 published both, so
`pip show darkmatter-sdk` and the PyPI page printed a name to anyone who
looked. PyPI cannot rewrite the metadata of a published version, so the only
repair was a new release — and the only way to stop it happening again is a
test that fails the build.

The identifiers are assembled from fragments so that this file does not
match its own list.
"""
import os
import subprocess
import sys

BANNED = ["ben" + "gunvl", "Ben" + " Gunvl", "cullaj" + "07"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "dist", "build", "__pycache__", ".venv", "venv"}
TEXT_EXT = {".py", ".md", ".txt", ".toml", ".cfg", ".json", ".yml", ".yaml"}


def _tracked_text_files():
    """Only files git actually tracks. Build directories regenerate from
    setup.py, so scanning them reports the same fault twice."""
    try:
        out = subprocess.check_output(
            ["git", "-C", ROOT, "ls-files"], stderr=subprocess.DEVNULL
        ).decode("utf-8", "ignore")
        names = [n for n in out.splitlines() if n.strip()]
    except Exception:
        names = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and not d.endswith(".egg-info")]
            for fn in filenames:
                names.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return [n for n in names if os.path.splitext(n)[1].lower() in TEXT_EXT]


def test_no_tracked_file_names_a_person():
    offenders = []
    for rel in _tracked_text_files():
        path = os.path.join(ROOT, rel)
        try:
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", "ignore")
        except OSError:
            continue
        for banned in BANNED:
            if banned in text:
                offenders.append("{0} contains {1!r}".format(rel, banned))
    assert not offenders, (
        "personal identifiers in a public package:\n  " + "\n  ".join(offenders)
    )


def test_setup_metadata_is_institutional():
    """The fields that reach PyPI, checked by name rather than by scanning."""
    with open(os.path.join(ROOT, "setup.py"), "rb") as fh:
        setup_py = fh.read().decode("utf-8", "ignore")
    assert 'author="DarkMatter"' in setup_py, "author must be the project, not a person"
    # Split, for the same reason BANNED is: written whole, this line makes the
    # scan above fail on the file that performs it.
    personal_url = "github.com/ben" + "gunvl"
    assert personal_url not in setup_py, "links must not name a personal account"
    assert "darkmatterhub.ai" in setup_py


def test_readme_installs_this_package():
    """The distribution is darkmatter-sdk; the import name is darkmatter.

    README said `pip install darkmatter`, and `darkmatter` on PyPI belongs to
    an unrelated author. Every Python reader who followed the README installed
    a stranger's package and then hit an ImportError. This README is the long
    description, so the wrong line was printed on the PyPI page itself.
    """
    with open(os.path.join(ROOT, "README.md"), "rb") as fh:
        readme = fh.read().decode("utf-8", "ignore")
    assert "pip install darkmatter-sdk" in readme, "README must install this distribution"
    wrong = "pip install darkmatter" + chr(10)
    assert wrong not in readme, (
        "README installs the package named darkmatter, which is not ours"
    )


if __name__ == "__main__":
    test_no_tracked_file_names_a_person()
    test_setup_metadata_is_institutional()
    test_readme_installs_this_package()
    print("identifiers clean; setup metadata institutional; README installs darkmatter-sdk")
    sys.exit(0)
