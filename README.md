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
git clone https://github.com/quaternionmedia/codecartographer.git
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
8. Go to your local codecartographer repo in file explorer
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
docker-compose -f ./graphbase/docker-compose.yml up --build -d && docker-compose -f ./docker-compose.yml up --build -d
```

_If you have problems with the above command, docker compose up graphbase, then docker compose up codecartographer_

# Usage (dev)

### Site

Once Docker containers are up, run the site by going to the codecartographer/web directory and running npm run dev.

```
cd web
npm install (only the first time)
npm run dev
```

Site will be running on localhost:1234

### Demo

Click the Demo button in the top right to see a plot of a simple code graph.

### Parse Github Repo

Input a public github repository into the text field.

Click 'Submit'

The service will parse out the necessary information from the repo and open the file directory panel.

You can collapse the panel by clicking the yellow arrow button attached to the side of the panel.

You can open the panel by clicking the same yellow arrow button on the left hand side.

### Plot Code Files

Once the file directory panel has been populated and opened, click any compatible file (the highlighted ones).

The service will begin reading the file url and plot a graph representing the file.

The graph is created using the Gravis library.

### Saved Graphs

Not implemented quite yet

### Docker Down

```
docker-compose -f docker-compose.yml down -v && docker-compose -f ./graphbase/docker-compose.yml down -v
```

_If you have problems with the above command, docker compose down codecartographer, then docker compose down graphbase_

# Test (dev)

**Note:** Tests are not implemented yet.
