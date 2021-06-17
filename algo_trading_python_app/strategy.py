import copy
import pickle
from datetime import timedelta
from tensorflow.keras.models import load_model

import pandas as pd

from config import MODEL_FILE
from logger_sender import Logger

from trade import Trade


class Strategy:
    def __init__(self, cfg: dict, predictions=None):
        self.log_to_stdout = cfg["log_to_stdout"]
        self.data_for_df = []
        self.logger = Logger(index=cfg["logger"]["index_name"],
                             url=cfg["logger"]["rabbit_url"],
                             queue="logs",
                             to_elk=cfg["log_to_elk"])
        self.log_run_name = cfg["run_name"]
        self.tp = cfg["params"].get("tp", None)
        self.sl = cfg["params"].get("sl", None)
        self.ttl = cfg["params"].get("ttl", None)
        self.fee = cfg["params"]["trade_fee"]
        self.capital = cfg["params"]["initial_capital"]
        self.position_capital = None
        self.max_position_capital = 100
        self.position_entry_price = None
        self.position_size = None
        self.position_entry_time = None
        self.buy_fee = None
        self.model_type = cfg["model"]
        self.model = self.__load_model(MODEL_FILE[cfg["model"]])
        self.classes = cfg["classes"]
        self.trades = []
        self.current_price = None
        self.current_timestamp = None
        self.trade_df: pd.DataFrame = None
        self.predictions = predictions

    def __load_model(self, model_file_name):
        if self.model_type == "NN" or self.model_type == "LSTM":
                return load_model(model_file_name)
        else:
            return pickle.load(open(model_file_name, "rb"))

    def __get_model_prediction(self, data):
        if self.model_type == "NN" or self.model_type == "LSTM":
            return self.model.predict_classes(data)
        else:
            return self.model.predict(data)

    def init_predictions(self, X):
        self.predictions = self.__get_model_prediction(X)

    def notify(self, timestamp, timestamp_idx, current_price):
        self.current_price = current_price
        self.current_timestamp = timestamp

        if len(self.trades) and not self.trades[-1].ended():
            self.trades[-1].update_lowest_price(current_price)

        if pd.isna(timestamp_idx):
            # we are in a minute between timeframes
            if self.position_entry_price:  # already in a position
                self.end_order_checks()
            return

        prediction = self.predictions[int(timestamp_idx)]

        # print("Time: {}. Capital: {}".format(timestamp, self.capital))

        log_context = {
            "@time": timestamp.isoformat(),
            "price": current_price,
            "log_type": "model_prediction",
            "run_name": self.log_run_name,
        }

        if self.classes == 3:
            if prediction[0] == 0:  # buy
                log_context["prediction"] = "buy"
                if self.position_entry_price:  # already in a position
                    self.end_order_checks()
                else:
                    self.buy()
            elif prediction[0] == 1:  # hold
                log_context["prediction"] = "hold"
                if self.position_entry_price:  # already in position
                    self.end_order_checks()
            elif prediction[0] == 2:  # sell
                log_context["prediction"] = "sell"
                if not self.position_entry_price:  # no position opened, do nothing
                    pass
                else:
                    self.sell()
            else:
                raise Exception("unknown prediction {}".format(prediction[0]))
        else:
            if prediction[0] == 0:  # buy
                log_context["prediction"] = "buy"
                if self.position_entry_price:  # already in a position
                    self.end_order_checks()
                else:
                    self.buy()
            elif prediction[0] == 1:  # sell
                log_context["prediction"] = "sell"
                if not self.position_entry_price:  # no position opened, do nothing
                    pass
                else:
                    self.sell()
            else:
                raise Exception("unknown prediction {}".format(prediction[0]))

        self.logger.log(log_context, stdout=False)

    def sell(self, tp_hit=False, sl_hit=False, ttl_hit=False):
        sell_fee = self.fee * self.position_size * self.current_price  # fee in usd
        profit = self.current_price * self.position_size * (1 - self.fee) - self.position_capital
        self.capital = self.capital + profit
        if self.log_to_stdout:
            print("Sell {:.6f} btc, price {}, fee{:.6f} usd. Total fees: {:.6f}. Profit/Loss: {:.6f} usd ({:.6f}% - fee included). "
                  "Price change: {:.6f} % (fee not included). Position duration: {} m".
                  format(self.position_size, self.current_price, sell_fee, self.buy_fee + sell_fee,
                         profit,
                         profit / self.position_capital,
                         (self.current_price - self.position_entry_price) / 100,
                         (self.current_timestamp - self.position_entry_time).seconds // 60))
        self.position_capital = None
        self.position_size = None
        self.position_entry_price = None
        self.position_entry_time = None
        self.buy_fee = None
        end_reason = "ml_model"
        if tp_hit:
            end_reason = "tp_hit"
        elif sl_hit:
            end_reason = "sl_hit"
        elif ttl_hit:
            end_reason = "ttl_hit"

        self.trades[-1].end_trade(sell_price=self.current_price, sell_fee=sell_fee, end_time=self.current_timestamp, end_reason=end_reason)
        trade_dict = copy.deepcopy(self.trades[-1].__dict__)
        trade_dict.update({
            "@time": trade_dict["end_time"].isoformat(),
            "run_name": self.log_run_name,
            "log_type": "trade",
            "start_time": trade_dict["start_time"].isoformat(),
            "end_time": trade_dict["end_time"].isoformat()
        })
        self.data_for_df.append(trade_dict)
        self.logger.log(trade_dict, stdout=False)
        # if self.log_to_stdout:
        #     print("Capital {}. Current timestamp: {}".format(self.capital, self.current_timestamp))

    def buy(self):
        self.position_entry_price = self.current_price
        self.position_capital = min(self.capital, self.max_position_capital)
        # self.position_capital = 0.8 * self.capital
        self.buy_fee = self.fee * self.position_capital
        self.position_size = self.position_capital * (1 - self.fee) / self.current_price
        self.position_entry_time = self.current_timestamp
        if self.log_to_stdout:
            print("Buy {:.6f} btc, price {}, fee {:.6f} usd".format(self.position_size, self.position_entry_price, self.buy_fee))
        self.trades.append(Trade(before_trade_capital=self.capital,
                                 position_capital=self.position_capital,
                                 entry_price=self.position_entry_price,
                                 buy_fee=self.buy_fee, size=self.position_size,
                                 start_time=self.position_entry_time, fee_percentage=self.fee,
                                 sl=self.sl, tp=self.tp, ttl=self.ttl))

    def end_order_checks(self):
        if self.tp:
            self.check_tp()
        if self.position_entry_price and self.sl:
                self.check_sl()
        if self.position_entry_price and self.ttl:
                self.check_ttl()

    def check_tp(self):
        if self.position_entry_price + self.position_entry_price * self.tp <= self.current_price:
            if self.log_to_stdout:
                print("$$$$$$ TP HIT!")
            self.sell(tp_hit=True)

    def check_sl(self):
        if self.current_price < self.position_entry_price - self.position_entry_price * self.sl:
            if self.log_to_stdout:
                print("@@@@@@@ SL HIT!")
            self.sell(sl_hit=True)

    def check_ttl(self):
        if self.current_timestamp - self.position_entry_time >= timedelta(minutes=self.ttl):
            if self.log_to_stdout:
                print("@@@@@@ TTL HIT!")
            self.sell(ttl_hit=True)

    def end(self):
        if not self.trades[-1].ended():
            self.trades.pop()
        self.trade_df = pd.DataFrame(self.data_for_df)
