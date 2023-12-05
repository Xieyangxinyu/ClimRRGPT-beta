# callm
Climate Action Through Large Language Models

## Pre-requisites
We use Python 3.11.6 and [Poetry](https://python-poetry.org/) to manage dependencies. 

We recommend using [pyenv](https://github.com/pyenv/pyenv) to manage your python versions. To switch to Python 3.11.6, run 
```
pyenv install 3.11.6
pyenv local 3.11.6
```

To After pulling from github, in your ``callm`` folder, do the following to install the dependencies:
```
poetry build
poetry install # install dependencies
poetry shell # make a virtual environment
```

If you would like to exit the virtual environment, run
```
exit # exit shell
```

Lastly, create a ``.env`` file in the root directory of the project and add the following:
```
OPENAI_API_KEY=<your openai api key>
model=<your model name> # e.g. gpt-4-1106-preview
```
Please check [OpenAI Model Pricing](https://openai.com/pricing) before choosing a model.

All data are available under the ``data`` folder. You can download all the data from this [Box Link](https://anl.box.com/s/wm888zovyapyou1txae7g75ghpc7sxre).

## Usage
We use [Streamlit](https://streamlit.io) to create a web app. To run the web app, run
```
streamlit run src/wildfireChat.py
```