import json
import time
import pprint
import os

import joblib
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import timedelta

from strategy import Strategy
from utils import extend_dataset_with_window_length


class Backtester:
    def __init__(self, config: dict):
        self.log_to_stdout = config["log_to_stdout"]
        self.scaler: MinMaxScaler = self.load_scaler(config["scaler"])
        self.close_price = None
        self.data: pd.DataFrame = self.load_data(config["dataset"])
        self.closing_minute_df = self.load_closing_minute_data()
        self.config = config
        self.X, self.Y = self.preprocess()
        self.strategy = None
        self.start_time = None
        self.duration = None
        self.results_json = None

    def init_strategy(self, config):
        if self.strategy:
            predictions = self.strategy.predictions
            self.strategy = Strategy(config, predictions)
        else:
            self.strategy = Strategy(config)
            self.strategy.init_predictions(self.X)

    def start(self):
        self.start_time = time.time()
        # should you use Y ?
        df_data = {
            "timestamp_data": list(range(len(self.X))),
            "open_time": self.data.index[self.config["window_length"]-1:],
            "closing_prices": self.close_price.iloc[self.config["window_length"]-1:],
        }

        timestamp_data = pd.DataFrame(df_data)
        timestamp_data.set_index("open_time", inplace=True)

        # timestamp_data.index = pd.to_datetime(timestamp_data.index)
        self.closing_minute_df = self.closing_minute_df[timestamp_data.index[0]:timestamp_data.index[-1]+timedelta(minutes=1)]
        backtest_df = self.closing_minute_df.join(timestamp_data)

        if self.config["timeframe"] > 1:
            backtest_df["closing_prices"] = backtest_df["closing_prices"].shift(self.config["timeframe"]-1)
            backtest_df["timestamp_data"] = backtest_df["timestamp_data"].shift(self.config["timeframe"]-1)
        # print(backtest_df.head(50))
        for row in zip(backtest_df.index, backtest_df["timestamp_data"], backtest_df["close"]):
            self.strategy.notify(row[0], row[1], row[2])

        self.strategy.end()
        self.duration = (time.time() - self.start_time)
        self.results_json = self.get_result_json()
        config_and_results = {
            "config": self.config,
            "results": self.results_json
        }

        pprint.pprint(self.results_json)

        print("& {} \\newline {} \\newline {} & {} \\newline {} \\newline {} &	{} & {} &	{} & {} & {} & {} & {} \\\\"
              .format(self.config["model"],
                      self.config["timeframe"],
                      self.config["window_length"],
                      self.config["params"].get("tp","-"),
                      self.config["params"].get("sl", "-"),
                      self.config["params"].get("ttl", "-"),
                      self.results_json["end_capital"],
                      round(self.results_json["win_%"]*100,2),
                      round(self.results_json["mean_loss"] * 100,2),
                      round(self.results_json["mean_profit"] * 100,2),
                      round(self.results_json["tp_hit_%"],2),
                      round(self.results_json["sl_hit_%"],2),
                      round(self.results_json["ttl_hit_%"],2)))

        if not os.path.exists("runs"):
            os.mkdir("runs")

        with open("runs/{}_cfg.pickle".format(self.config["run_name"]), "w") as fout:
            fout.write(json.dumps(config_and_results, indent=4))
        trade_df_file = "runs/{}_trades.csv".format(self.config["run_name"])
        self.strategy.trade_df.to_csv(trade_df_file)

        if self.log_to_stdout:
            print("Backtesting DONE! Saved to file")

    def load_scaler(self, scaler_path):
        return joblib.load(scaler_path)

    def load_data(self, dataset_path):
        df = pd.read_csv(dataset_path)
        df.set_index("open_time", inplace=True)
        self.close_price = df["close"]
        df.drop(columns=["close"], inplace=True)
        if self.log_to_stdout:
            print("Loaded {} with shape {}".format(dataset_path, df.shape))
        df.index = pd.to_datetime(df.index)
        return df

    def preprocess(self):
        data = self.data.to_numpy()
        X = data[:, :-1]
        Y = data[:, -1]
        X, Y = extend_dataset_with_window_length(X, Y, self.config["window_length"])
        if self.log_to_stdout:
            print("X.shape: {}, Y.shape: {}".format(X.shape, Y.shape))
        X = self.scaler.transform(X)
        if self.config["model"] == "LSTM":
            X = X.reshape((X.shape[0], self.config["window_length"], X.shape[1] // self.config["window_length"]))

        return X, Y

    def get_result_json(self):
        df = self.strategy.trade_df
        result = {
            "end_capital": round(self.strategy.capital, 2),
            "number_of_trades": len(df),
            "winning_trades": len(df[df["trade_verdict"] == "WIN"]),
            "losing_trades": len(df[df["trade_verdict"] == "LOSS"]),
            "win_%": round(
                len(df[df["trade_verdict"] == "WIN"]) / len(df), 4),
            "profit_loss_mean_ratio": round(abs(
                df[df["trade_verdict"] == "WIN"]["profit_percentage"].mean() / df[df["trade_verdict"] == "LOSS"][
                    "profit_percentage"].mean()), 4),
            "mean_loss": round(df[df["trade_verdict"] == "LOSS"]["profit_percentage"].mean(), 4),
            "mean_profit": round(df[df["trade_verdict"] == "WIN"]["profit_percentage"].mean(), 4),
            "model_end_trade_%": round(len(df[df["end_reason"] == "ml_model"]) / len(df) * 100, 4),
            "tp_hit_%": round(len(df[df["end_reason"] == "tp_hit"]) / len(df) * 100, 4),
            "sl_hit_%": round(len(df[df["end_reason"] == "sl_hit"]) / len(df) * 100, 4),
            "ttl_hit_%": round(len(df[df["end_reason"] == "ttl_hit"]) / len(df) * 100, 4),
            "avg_trade_len": int(df["trade_duration"].mean()),
            "total_fees_usd": round(df["total_fee"].sum(), 4),
            "total_win_usd": round(df[df["trade_verdict"] == "WIN"]["profit"].sum(), 4),
            "total_loss_and_fees_usd": round(df[df["trade_verdict"] == "LOSS"]["profit"].sum(), 4),
            "run_time": self.duration,
            "max_drawdown": df["max_drawdown"].max(),
            "max_drawdown_winning_trade": df[df["trade_verdict"] == "WIN"]["max_drawdown"].max(),
            "highest_possible_win": df["highest_possible_win"].max(),
            "highest_possible_win_losing_trade": df[df["trade_verdict"] == "LOSS"]["highest_possible_win"].max()
        }

        if self.config["params"].get("sl", None) is not None and self.config["params"].get("tp", None) is not None:
            result["R_R"] = round(self.config["params"]["tp"] / self.config["params"]["sl"], 4)
        else:
            result["R_R"] = None

        return result

    def load_closing_minute_data(self):
        min_df = pd.read_csv("minute_close_prices.csv")
        min_df.set_index("open_time", inplace=True)
        min_df.index = pd.to_datetime(min_df.index)
        return min_df
