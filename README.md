# conda cpm

Simple tool to generate minimal versions of Conda environments, also including
`pip` dependencies, for cross-platform sharing.

Built on top of [`conda tree`](https://github.com/conda-incubator/conda-tree) and [`pipdeptree`](https://github.com/tox-dev/pipdeptree). Inspired by [`conda minify`](https://github.com/jamespreed/conda-minify).

## Why use `conda cpm`?

-   Conda (especially with mamba) is a great tool to manage Python virtual
    environments, especially if you need to install some non-Python dependencies,
    or use compiled dependencies like CUDA. See
    <https://aseifert.com/p/python-environments/> for more on this.

-   I use Conda preferentially to install any packages available through it; and
    provide my virtualenv&rsquo;s Python version through Conda.

-   Some packages are not easily accessible on Conda, and I use `pip` or `poetry`
    (or `hatch` or your other tool of choice) to pull those packages in.

-   This approach works remarkably well, but when it is time to share my
    environment with others, there are several ways to do it, and they are subtly
    different in capabilities and issues.

    e.g

    -   `conda env export`, `conda env export --from-history`, `conda list --export`

    -   For pip-installed packages, `pip freeze`, `pip list --freeze`, or whatever
        your favorite Python package manager provides.

    -   conda-lock, pipenv, and other lock file generating tools

-   If the exported file is too specific, specifying every dependency and build
    identifier, it often cannot be reproduced on a different platform because
    these are not portable.

-   If you use both `conda` and `pip`, these tools will typically be unaware of
    each other, generating overlapping requirements files.

## How does `conda cpm` solve this?

-   `conda cpm` constructs a minimal `environment.yml` file, with only the
    "leaves" of the dependency tree, both for `pip` and `conda`.

-   It retains information about which packages came from Conda and which came
    from Pip, but does not include dependencies in the export.

-   It specifies exact versions by default, but it can optionally relax the
    version requirements to being flexible at the patch level or minor level
    (semver).

-   It can optionally include info about which Conda channel a package came from,
    the Python version, or any manually specified packages.

-   It does not include system-specific information like the Conda environment
    prefix.

## Installation

### via pip

```console
pip install conda-pip-minimal
```

### via pipx

```console
pipx install conda-pip-minimal
```

### Run without installing

```console
pipx run conda-pip-minimal --help
```

## Usage

The script for this package is named `conda-cpm`; so it can be run like `conda cpm`

```console
$ conda cpm [OPTIONS]
```

### Options:

  * `-p, --prefix PATH`: Conda env prefix
  * `-n, --name TEXT`: Conda env name
  * `--pip / --no-pip`: Include pip dependencies  [default: True]
  * `--relax [none|major|minor|full]`: [default: full]
  * `--include TEXT`: Packages to always include  [default: python, pip]
  * `--exclude TEXT`: Packages to always exclude  [default: ]
  * `--channel / --no-channel`: Add channel to conda dependencies  [default: False]
  * `--debug / --no-debug`: [default: False]
  * `--help`: Show this message and exit.

## Examples

Here are a few example runs for this package:

### From within the conda environment:

``` shell
❯ conda cpm
dependencies:
- python=3.8.13
- pip=22.2.2
- pip:
  - conda-pip-minimal==0.1.0
  - ipython==8.5.0
  - snoop==0.4.2
  - trio-typing==0.7.0
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Specifying the conda environment

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv
dependencies:
- pip=22.2.2
- python=3.8.13
- pip:
  - conda-pip-minimal==0.1.0
  - ipython==8.5.0
  - snoop==0.4.2
  - trio-typing==0.7.0
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Exclude packages

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv --exclude snoop --exclude trio-typing
dependencies:
- python=3.8.13
- pip=22.2.2
- pip:
  - conda-pip-minimal==0.1.0
  - ipython==8.5.0
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Include a normally-excluded dependency

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv --include trio
dependencies:
- trio=0.22.0
- pip:
  - conda-pip-minimal==0.1.0
  - ipython==8.5.0
  - snoop==0.4.2
  - trio-typing==0.7.0
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Specify conda channels

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv --channel
dependencies:
- conda-forge::python=3.8.13
- conda-forge::pip=22.2.2
- pip:
  - conda-pip-minimal==0.1.0
  - ipython==8.5.0
  - snoop==0.4.2
  - trio-typing==0.7.0
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Relax versions

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv --relax minor
dependencies:
- python=3.8.*
- pip=22.2.*
- pip:
  - conda-pip-minimal==0.1.*
  - ipython==8.5.*
  - snoop==0.4.*
  - trio-typing==0.7.*
name: /home/venky/dev/conda-pip-minimal/.venv
```

### Skip pip dependencies

Why would you want to do this, though?

``` shell
❯ conda cpm --prefix ~/dev/conda-pip-minimal/.venv --no-pip
dependencies:
- pip=22.2.2
- python=3.8.13
name: /home/venky/dev/conda-pip-minimal/.venv
```
