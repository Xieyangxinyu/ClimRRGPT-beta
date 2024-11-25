# callm
Climate Action Through Large Language Models

## Pre-requisites

Install [Ollama](https://github.com/ollama/ollama).

Once you have installed Ollama, you can run the following command to install Llama 3 language model:
```
ollama run llama3.1:8b-instruct-q4_0
```

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
model=<your model name  # e.g. gpt-4-1106-preview>
```
Please check [OpenAI Model Pricing](https://openai.com/pricing) before choosing a model.

Add ``src`` to your path by 
```
export PYTHONPATH="${PYTHONPATH}:src/"
```

All data are available under the ``data`` folder. You can download all the data from this [Box Link](https://anl.box.com/s/wm888zovyapyou1txae7g75ghpc7sxre).

## Usage
We use [Streamlit](https://streamlit.io) to create a web app. To run the web app, run
```
streamlit run src/modules/Welcome.py
```


## TODO
- [ ] Add Heat Index Data
  - unlike the other data, this data comes with 3 variables
    - Summer daily maximum heat index
    - Summer seasonal maximum heat index
    - Number of summer days with daily max heat index above 95 / 105 / 115 / 125 F
- [ ] Add Drought Data
  - unlike the other data, this data is in the form of a time series
  - which will be visualized as a line chart
  - and analyzed using time series analysis