# Moldovan Andrei - dissertation thesis application
# Algorithmic Bitcoin trading using machine learning and technical analysis

Download the BTCUSD dataset from https://www.kaggle.com/jorijnsmit/binance-full-history or using https://github.com/gosuto-ai/candlestick_retriever .

To start a rabbitmq and an elk stack run from the docker folder:
```sh
docker-compose up
```
if elk has some problems at start follow the details from https://hub.docker.com/r/sebp/elk .

The folder ml_training_and_tunning_colab_notebooks contains jupyter notebooks runnable in colab that are used to transform the previous dataset and to train and tune some ml models.

The kibana_dashboard.txt from the docker folder can be imported in kibana using the Import Dashboard API to display the results of a backtest run.

Setup the config.py file and run the backtest using
```sh
py -3.8 main.py
```
This should run with the dummy files that are present in the repository.

To run a strategy tunning use
```sh
py -3.8 main_tuner.py
```

