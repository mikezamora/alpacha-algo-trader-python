import os
from time import time_ns
import csv 
import _thread

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import ConciseDateFormatter

from alpaca.trading.client import TradingClient, OrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.stream import TradingStream

from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.models.quotes import Quote
from alpaca.data import CryptoDataStream

from alpaca.common.exceptions import APIError

from auth import Auth

class Crypto:

    def __init__(self):
        self.paper_trading = False
        self.SYMBOL = 'ETH/USD'
        self.POSITION_SYMBOL = 'ETHUSD'
        self.trail_percent = 0.0065

        self.auth = Auth()
        self.trading_client = TradingClient(self.auth.API_KEY, self.auth.API_SECRET, paper=self.paper_trading)
        self.trading_stream = TradingStream(self.auth.API_KEY, self.auth.API_SECRET, paper=self.paper_trading)
        self.market_data = CryptoHistoricalDataClient(self.auth.API_KEY, self.auth.API_SECRET)
        self.crypto_stream = CryptoDataStream(self.auth.API_KEY, self.auth.API_SECRET)
        
        self.pnl = 0.0
        self.last_trailing_update_seconds = time_ns() / 1e+9
        self.last_stat_print_seconds = time_ns() / 1e+9
        self.last_thread_reset_seconds = time_ns() / 1e+9
        self.highest_trailing_price = 0.0
        self.lowest_trailing_price = 1000000000.00
        self.buy_price = 0.0
        self.passed_sell_on_upward_trend = False

        self.first_run = True

        self.report_name = 'output.csv'
        self.csv_file = None
        self.csv_writer = None

        self.report_name_chart = 'output_chart.csv'
        self.csv_file_chart = None
        self.csv_writer_chart = None

        plt.style.use('dark_background')
        self.fig, self.ax1 = plt.subplots(figsize=(10, 5), layout='constrained')
        self.ani = None
        self.chart_data = []

    def start_algo(self):
        # clean up output directory
        if os.path.exists(self.report_name):
            os.remove(self.report_name)
        else:
            print('{} does not exist, creating report file'.format(self.report_name))
        
        self.csv_file = open(self.report_name, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file, dialect='excel', delimiter=',')

        self.csv_writer.writerow(['timestamp', 'bid', 'ask', 'current', 'highest', 'lowest', 'percent_change_highest', 'percent_change_lowest', 'profit & loss', 'attempted_buy', 'attempted_sell'])

        # start charting
        def setup_animation():
            if os.path.exists(self.report_name_chart):
                os.remove(self.report_name_chart)
            else:
                print('{} does not exist, creating report file'.format(self.report_name_chart))
            
            self.csv_file_chart = open(self.report_name_chart, 'w', newline='')
            self.csv_writer_chart = csv.writer(self.csv_file_chart, dialect='excel', delimiter=',')

            self.csv_writer_chart.writerow(['timestamp', 'bid', 'ask', 'current', 'highest', 'lowest', 'buy_price', 'sell_price', 'stop_loss_price'])

            self.ani = animation.FuncAnimation(self.fig, animate, interval=1000)
            print('start animation')
            plt.show()

        def animate(i):
            dataArray = self.chart_data

            x_bid = []
            y_bid = []

            x_ask = []
            y_ask = []

            x_current = []
            y_current = []

            x_high = []
            y_high = []

            x_low = []
            y_low = []

            x_buy = []
            y_buy = []

            x_sell = []
            y_sell = []

            x_stop = []
            y_stop = []

            index = 0.0
            for eachLine in dataArray:
                if len(eachLine)>1:
                    timestamp, bid,ask,current,highest,lowest,buy,sell,stop = eachLine

                    x_bid.append(index)
                    y_bid.append(bid)
                    x_ask.append(index)
                    y_ask.append(ask)
                    x_current.append(index)
                    y_current.append(current)
                    x_high.append(index)
                    y_high.append(highest)
                    x_low.append(index)
                    y_low.append(lowest)
                    x_buy.append(index)
                    y_buy.append(buy)
                    x_sell.append(index)
                    y_sell.append(sell)
                    x_stop.append(index)
                    y_stop.append(stop)

                    index += 1

            self.ax1.clear()

            # self.ax1.plot(x_bid, y_bid, linewidth=2, linestyle=':', label='bid')
            # self.ax1.plot(x_ask, y_ask, linewidth=2, linestyle=':', label='ask')

            self.ax1.plot(x_low, y_low, linewidth=2, linestyle='--', label='lowest')
            self.ax1.plot(x_high, y_high, linewidth=2, linestyle='--', label='highest')
            
            self.ax1.plot(x_buy, y_buy, linewidth=2, linestyle=':', label='buy')
            self.ax1.plot(x_sell, y_sell, linewidth=2, linestyle=':', label='sell')
            self.ax1.plot(x_stop, y_stop, linewidth=2, linestyle='-.', label='stop')

            self.ax1.plot(x_current, y_current, linewidth=2, linestyle='-', label='current')
            self.ax1.legend()
            # cdf = ConciseDateFormatter(self.ax1.xaxis.get_major_locator())
            # self.ax1.xaxis.set_major_formatter(cdf)
            

        # Clean up any stale trades
        self.close_all()

        self.asset = self.trading_client.get_asset(self.SYMBOL)
        print(self.asset)

        async def trade_update_handler(data):
            print(data)

        self.trading_stream.subscribe_trade_updates(handler=trade_update_handler)
        _thread.start_new_thread(self.trading_stream.run, ())

        async def quote_data_handler_wrapper(data: Quote):
            # print(data)
            self.quote_data_handler(data)

        

        def crypto_stream_wrapper():
            _thread.start_new_thread(self.crypto_stream.run, ())
            while True: 
                current_time_second = time_ns() / 1e+9
                time_diff = current_time_second - self.last_thread_reset_seconds
                if(time_diff >= 10):
                    self.last_thread_reset_seconds = current_time_second
                    self.crypto_stream.stop()

                    self.crypto_stream = CryptoDataStream(self.auth.API_KEY, self.auth.API_SECRET)
                    self.crypto_stream.subscribe_quotes(quote_data_handler_wrapper, self.SYMBOL)
                    _thread.start_new_thread(self.crypto_stream.run, ())

        _thread.start_new_thread(crypto_stream_wrapper, ())
        setup_animation()
    

    def close_all(self):
        # Check Open Position
        position = self.trading_client.get_open_position(self.POSITION_SYMBOL)
        
        # closes all position AND also cancels all open orders
        if (float(position.cost_basis) > 2.0):
            self.trading_client.close_all_positions(cancel_orders=True)


    def quote_data_handler(self, data: Quote):
        market_price = (data.ask_price + data.bid_price) / 2

        # Check Account Buying Power
        balance = self.trading_client.get_account()
        portfolio_value = float(balance.portfolio_value)
        buying_power = float(balance.buying_power)

        # Check Asset balance
        cost_basis = 0.0
        position = None
        try:
            position = self.trading_client.get_open_position(self.POSITION_SYMBOL)
            cost_basis = float(position.cost_basis)
        except APIError:
            print('No position found for {}'.format(self.POSITION_SYMBOL))

        # reset lowest trailing price to highest trailing price if asset is majorly trending upwards 
        if (self.lowest_trailing_price * (1 + self.trail_percent) < market_price):
            print('reset lowest trailing price to highest trailing price if asset is majorly trending upwards. lowest: {:.4f} | highest: {:.4f}'.format(self.lowest_trailing_price, self.highest_trailing_price))
            self.lowest_trailing_price = self.highest_trailing_price

        if (market_price > self.highest_trailing_price): 
            print('new highest trailing price: {:.4f}'.format(market_price))
            self.highest_trailing_price = market_price

        if (market_price < self.lowest_trailing_price):
            print('new lowest trailing price: {:.4f}'.format(market_price))
            self.lowest_trailing_price = market_price

        # Check Profit/Loss
        self.pnl = 0.0
        if (position != None):
            self.pnl = float(position.unrealized_pl)

        percent_change_highest = 1 - (market_price / self.highest_trailing_price)
        percent_change_lowest = 1 - (market_price / self.lowest_trailing_price)
        
        attempted_buy = False
        attempted_sell = False

        buy_price = self.highest_trailing_price - 2

        trending_down = market_price - self.lowest_trailing_price < 1

        # Buy if asset balance is too low
        if (buy_price >= market_price and cost_basis < 2 and not trending_down):
            # purchase_amount_usd = buying_power - (portfolio_value / 2) - cost_basis
            purchase_amount_usd = buying_power
            attempted_buy = True
            if (purchase_amount_usd >= 2.00):
                order_data = OrderRequest(symbol=self.SYMBOL, 
                    side=OrderSide.BUY, 
                    type=OrderType.MARKET, 
                    time_in_force=TimeInForce.GTC, 
                    notional=purchase_amount_usd)
                order = self.trading_client.submit_order(order_data)
                self.highest_trailing_price = market_price
                self.lowest_trailing_price = market_price
                self.buy_price = market_price
                print('max price: {:.4f} | min price: {:.4f} | current price: {:.4f} | percent change high/low: {:.6f}/{:.6f} | Profit & Loss: {:.4f}'.format(self.highest_trailing_price, self.lowest_trailing_price, market_price, percent_change_highest, percent_change_lowest, self.pnl))
                print('Buy Requested - Status: {}, Amount: {} @ {}'.format(order.status, purchase_amount_usd, market_price))

        # after purchase Set Limit Sell if loss is more than (z) percentage from highest price during tracking
        current_time_second = time_ns() / 1e+9
        time_diff = current_time_second - self.last_trailing_update_seconds

        sell_price = self.lowest_trailing_price + 2
        stop_loss_price = self.buy_price - 2.5

        market_price_greater_than_sell_price = market_price >= sell_price
        market_price_less_than_sell_price = market_price <= sell_price
        market_price_less_than_stop_price = market_price < stop_loss_price

        # turning stop loss off
        market_price_less_than_stop_price = False

        trending_up = self.highest_trailing_price - market_price < 1

        if (trending_up):
            if (market_price_greater_than_sell_price and cost_basis >= 2.00):
                self.passed_sell_on_upward_trend = True

            if (market_price_less_than_sell_price): 
                trending_up = False

        if (position != None and (market_price_greater_than_sell_price or market_price_less_than_stop_price or self.passed_sell_on_upward_trend) and not trending_up and cost_basis >= 2.00):
            attempted_sell = True
            order_data = OrderRequest(symbol=self.SYMBOL, 
                side=OrderSide.SELL, 
                type=OrderType.MARKET, 
                time_in_force=TimeInForce.GTC, 
                qty=position.qty)
            if (time_diff > 2.5):
                order = self.trading_client.submit_order(order_data)
                self.highest_trailing_price = market_price
                self.lowest_trailing_price = market_price
                self.last_trailing_update_seconds = current_time_second
                self.passed_sell_on_upward_trend = False

                print('max price: {:.4f} | min price: {:.4f} | current price: {:.4f} | percent change high/low: {:.6f}/{:.6f} | Profit & Loss: {:.4f}'.format(self.highest_trailing_price, self.lowest_trailing_price, market_price, percent_change_highest, percent_change_lowest, self.pnl))
                print('Trailing Stop Sell Requested - Status: {}, Amount: {} @ -{}%'.format(order.status, position.qty, self.trail_percent))

        time_diff = current_time_second - self.last_stat_print_seconds

        if(time_diff > 1*5):
            self.last_stat_print_seconds = current_time_second
            print(data)
            print('max price: {:.4f} | min price: {:.4f} | current price: {:.4f} | percent change high/low: {:.6f}/{:.6f} | Profit & Loss: {:.4f}'.format(self.highest_trailing_price, self.lowest_trailing_price, market_price, percent_change_highest, percent_change_lowest, self.pnl))

        # headers ['timestamp', 'bid', 'ask', 'current', 'highest', 'lowest', 'percent_change_highest', 'percent_change_lowest', 'profit & loss', 'attempted_buy', 'attempted_sell']
        self.csv_writer.writerow([data.timestamp.isoformat(), data.bid_price, data.ask_price, market_price, self.highest_trailing_price, self.lowest_trailing_price, percent_change_highest, percent_change_lowest, self.pnl, attempted_buy, attempted_sell])
        
        if(stop_loss_price <= 0):
            stop_loss_price = market_price

        chart_data = [data.timestamp.isoformat(), data.bid_price, data.ask_price, market_price, self.highest_trailing_price, self.lowest_trailing_price, buy_price, sell_price, stop_loss_price]
        self.csv_writer_chart.writerow(chart_data)
        if(len(self.chart_data) > 300):
            self.chart_data.pop(0)
        self.chart_data.append(chart_data)
        self.first_run = False
