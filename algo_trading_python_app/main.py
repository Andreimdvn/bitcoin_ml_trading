from backtest import Backtester
from config import config_dict


def main():
    tester = Backtester(config_dict)
    tester.init_strategy(config_dict)
    tester.start()
    print("elapsed: ", tester.duration)


if __name__ == "__main__":
    main()
