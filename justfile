default:
    just --list

build:
    poetry build

update_version_patch:
    poetry version patch

publish:
    poetry publish

pipx_install:
    pipx install --force dist/conda_pip_minimal-$(poetry version | perl -lane 'print $F[1]')*.whl
