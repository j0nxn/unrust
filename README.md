# README

## prerequisites

### windows

- python
- ghidra
  - windbg
- GNU Make
- bash
- rust
  - msvc

## install

    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt

## configure

### windows

    $env:GHIDRA_INSTALL_DIR="C:\Path\To\Ghidra\Installation"

### unix

    export GHIDRA_INSTALL_DIR="/path/to/ghidra/installation"

## run

    .\venv\Scripts\Activate.ps1 # windows
    source venv/bin/activate    # unix

    make top=100 dataset.csv
