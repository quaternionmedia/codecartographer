# Codecarto: 

Development tool for mapping source code

Create graphs

Plot the graphs.

Create JSON object of the graph.

# Installation

<details>
<summary>PyPi not implemented yet</summary>

### From pypi:

```
python -m venv venv

.\venv\Scripts\activate

pip install codecarto

```

</details>

### From Git (dev):

Clone the repo

```
git clone git@github.com:quaternionmedia/codecarto.git
git submodule init
git submodule update
```

Open a shell terminal, navigate to CodeCartographer folder

Setup virtual environment

```
python -m venv venv
.\venv\Scripts\activate
```

Install dependencies

```
poetry install
```

Install graphbase module

```
pip install -m graphbase
```

Docker Up

```
docker-compose -f ./codecarto/graphbase/docker-compose.yml up --build -d && docker-compose -f ./codecarto/docker-compose.yml up --build -d
```

# Usage (dev)

### Site

Go to localhost:2000 to see the CodeCarto site.

### Parser

Click Parser

Input github repo url

Click Parse

Look through contents for .py file

Click PLOT next to .py file to display the Plotter page

### Plotter

Select a layout

Click Single Plot to display the graph of the .py file

### Docker Down

```
docker-compose -f ./codecarto/docker-compose.yml down -v && docker-compose -f ./codecarto/graphbase/docker-compose.yml down -v
```

# Test (dev)

**Note:** Tests are not implemented yet.
