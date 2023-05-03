# Codecarto:
Development tool for mapping source code.

Create graphs. 

Plot the graphs. 

Create JSON object of graph.

---

## Installation

### From pypi:

    python -m venv venv

    .\venv\Scripts\activate

    pip install codecarto

### From Git:

clone repo  

open terminal

navigate to repo  

    python -m venv venv

    .\venv\Scripts\activate

    pip install -e .

---

## Usage
### Check output dir:
To show the current output directory 

    codecarto output

### Change output:
-s | --set : options can be used to set the output directory

If directory does not exist, will ask if you'd like to make it

    codecarto output -s DIR_PATH 

### Demo:
Parse the package source code

    codecarto demo 

### Passed file:
Can pass a file or running script of source code in. 

    codecarto FILE_PATH
