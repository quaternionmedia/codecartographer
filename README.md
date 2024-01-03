# Codecarto: 

Development tool for mapping source code
Visualize source code through graphs

# Installation

<details>
<summary>PyPi not implemented yet</summary>

## From pypi:

```
python -m venv venv

.\venv\Scripts\activate

pip install codecarto

```

</details>

## From Git (dev):

### Clone the repo

```
git clone git@github.com:quaternionmedia/codecarto.git
git submodule init
git submodule update
```

### Create a Github API token 

<details>
<summary>Create a Github API token</summary>
  
1. Login to Github 
2. Click Profile Image
3. Go to **Settings > Developer Settings (at the bottom of left pane) > Personal Access Tokens > Tokens (classic)**
    - Or go here https://github.com/settings/tokens
4. Click "Generate New Token" dropdown
5. Choose one of the token options
6. Check the "public_repo" checkbox
7. Copy the ghp token generated
8. Go to your local repo in file explorer
9. At the root, create a new text file named "token.txt"
    - PATH\TO\codecartographer\token.txt
10. Paste your ghp token into token.txt and save
    
</details>

### Start the project
Open a shell terminal, navigate to codecartographer repo folder

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
*If you have problems with the above command, docker compose up graphbase, then docker compose up codecartographer*

# Usage (dev)

### Site

Once Docker containers are up and running, go to localhost:2000 to see the CodeCarto site.

### Parser

Click Parser

Input github repo url (that has a .py file)

*More file types are in the works*

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
*If you have problems with the above command, docker compose down codecartographer, then docker compose down graphbase*

# Test (dev)

**Note:** Tests are not implemented yet.
