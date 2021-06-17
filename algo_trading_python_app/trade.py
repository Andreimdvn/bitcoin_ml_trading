class Trade:
    def __init__(self, before_trade_capital, position_capital, entry_price, buy_fee, size, start_time, fee_percentage, sl, tp, ttl):
        self.before_trade_capital = before_trade_capital
        self.position_capital = position_capital
        self.entry_price = entry_price
        self.buy_fee = buy_fee
        self.size = size
        self.start_time = start_time
        self.fee_percentage = fee_percentage
        self.sell_price = None
        self.sell_fee = None
        self.end_time = None
        self.end_reason = None

        self.trade_duration = None
        self.total_fee = None
        self.profit = None
        self.profit_percentage = None
        self.price_change = None
        self.trade_verdict = None

        self.lowest_price = entry_price
        self.highest_price = entry_price

        self.sl = sl
        self.tp = tp
        self.ttl = ttl

    def update_lowest_price(self, current_price):
        self.lowest_price = min(self.lowest_price, current_price)
        self.highest_price = max(self.highest_price, current_price)

    def end_trade(self, sell_price, sell_fee, end_time, end_reason: str):
        self.sell_price = sell_price
        self.sell_fee = sell_fee
        self.end_time = end_time
        self.end_reason = end_reason

        self.trade_duration = (self.end_time - self.start_time).seconds // 60
        self.total_fee = self.buy_fee + self.sell_fee

        self.profit = sell_price * self.size * (1 - self.fee_percentage) - self.position_capital

        self.profit_percentage = self.profit / self.position_capital
        self.price_change = (self.sell_price - self.entry_price) / 100

        self.max_drawdown = (self.entry_price - self.lowest_price) / self.entry_price
        self.highest_possible_win = (self.highest_price - self.entry_price) / self.entry_price

        if self.profit_percentage > 0:
            self.trade_verdict = "WIN"
        else:
            self.trade_verdict = "LOSS"

    def ended(self):
        return self.end_time is not None
