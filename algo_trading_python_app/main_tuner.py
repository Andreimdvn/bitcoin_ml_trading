from copy import deepcopy
import pandas as pd
import time

from backtest import Backtester
from config import config_dict

TUNE_TP = [None, 0.005, 0.01, 0.03, 0.05, 0.1]
TUNE_SL = [None, 0.005, 0.01, 0.03, 0.05, 0.1]
TUNE_TTL = [None, 180, 300, 420]


LOG_TO_ELK = False
RUN_NAME_PREFIX = "tunning_strategy_{}"
tester = None


def run_job(job: dict):
    cfg = deepcopy(config_dict)
    cfg["params"]["tp"] = job["tp"]
    cfg["params"]["sl"] = job["sl"]
    cfg["params"]["ttl"] = job["ttl"]
    cfg["log_to_elk"] = LOG_TO_ELK
    cfg["run_name"] = job["run_name"]

    global tester
    if not tester:
        tester = Backtester(cfg)
    tester.init_strategy(cfg)
    tester.start()
    job.update(tester.results_json)


def main():
    t = time.time()
    results = []
    idx_run = 0
    total_jobs = len(TUNE_TP) * len(TUNE_SL) * len(TUNE_TTL)


    for tp in TUNE_TP:
        for sl in TUNE_SL:
            for ttl in TUNE_TTL:
                job = {
                    "tp": tp,
                    "sl": sl,
                    "ttl": ttl,
                    "run_name": RUN_NAME_PREFIX.format(idx_run)
                }
                idx_run += 1
                print("Running {}/{} ".format(idx_run, total_jobs), job)
                run_job(job)
                results.append(job)

    results_df = pd.DataFrame(results)
    results_df.to_csv("tunning_{}_scenarios_{}_{}_timeframe_{}_window.csv".format(total_jobs, config_dict["model"],
                                                                                  config_dict["timeframe"],
                                                                                  config_dict["window_length"]))
    print("time: {}".format(time.time() - t))


if __name__ == "__main__":
    main()
