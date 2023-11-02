# Codecarto:

Development tool for mapping source code.

Create graphs.

Plot the graphs.

Create JSON object of the graph.

---

## Installation

### From pypi:

```
python -m venv venv

.\venv\Scripts\activate

pip install codecarto
```

### From Git [dev use]:

clone repo

open terminal

navigate to repo

```
python -m venv venv

.\venv\Scripts\activate

pip install -e .
```

---

## Usage

### Help Information

Check this first to see all usage information

```
codecarto help
```

### Check output dir:

To show the current output directory

```
codecarto output
```

### Change output:

-s | --set : options can be used to set the output directory

If directory does not exist, will ask if you'd like to make it

```
codecarto output -s DIR_PATH
```

### Demo:

Parse the package source code

```
codecarto demo
```

### Passed file:

Can pass a file or running script of source code in.

```
codecarto FILE_PATH
```

---

## Testing

Can test the package using nox commands.

### All Tests

```
nox
```

### Session Tests

Test the use of package as an imported library.

```
nox -s unit_test
```

Test the package CLI commands.

```
nox -s test_dir
nox -s test_help
nox -s test_output
nox -s test_palette
nox -s test_palette_import
nox -s test_palette_export
nox -s test_palette_reset
nox -s test_palette_types
nox -s test_palette_new
nox -s test_demo
nox -s test_empty
nox -s test_file
```
