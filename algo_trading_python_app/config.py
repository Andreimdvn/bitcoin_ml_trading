MODEL_FILE = {
    "logistic_regression": "logistic_regression_attempt_2_balanced.pickle",
    "NN": "nn_2__60minutes_30window.h5",
    "LSTM": "lstm_4__60minutes_30window.h5"
}

config_dict = {
    "log_to_elk": True,
    "classes": 2,
    "log_to_stdout": False,
    "dataset": "test_df_60minutes_1_candles_2_class.csv",
    "window_length": 30,
    "timeframe": 60,
    "scaler": "nn_scaler_60minutes_30window.save",
    "model": "NN",
    "params": {
        "tp": 0.05,  # x%
        # "sl": 0.05,  # y%
      # "ttl": 420,  # keep position for x minutes,
       "trade_fee": 0.00075,  # update it to 0.00075 to take into account bnb
       "initial_capital": 100,
    },
    "run_name": "nn_backtest_60_timeframe_30_window",
    "logger": {
        "index_name": "algo_tuning",
        "rabbit_url": "amqp://guest:guest@localhost:5672/",
    }
}
