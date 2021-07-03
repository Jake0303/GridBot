import backtrader as bt
import pandas as pd
import datetime
import asyncio
import pytz
import math
import threading
import sys
import os
import traceback
import logging
import webbrowser
from datetime import timedelta
logging.getLogger('matplotlib.font_manager').disabled = True
from btplotting import BacktraderPlottingLive
from btplotting.schemes import Tradimo
from btplotting import BacktraderPlotting
from backtrader.indicators.dma import MovAv
from btplotting.analyzers import RecorderAnalyzer
from ccxtbt import CCXTStore
from decimal import Decimal
from Indicators import gridline

# Accessing Bokeh's log - Walter
from bokeh.util import logconfig
logconfig.basicConfig(filename="output.log")

#Position Sizing by account size / close price
class AccountSizer(bt.Sizer):
    def _getsizing(self, comminfo, cash, data, isbuy):
        size = cash / data.close[0]
        return size
# gridPointsStrat
class GridBotStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(gridSize = 50)
    gridPoints = []
    def __init__(self):
        try:
            print("Starting...")
            self.buyline = dict()
            self.buyline = gridline.GridLine(self.datas[0])
        except Exception as e:
            print(e)
    def notify_data(self, data, status, *args, **kwargs):
        print('*' * 5, 'DATA NOTIF:', data._getstatusname(status), *args)
        if status == data.LIVE:
            self.data_live = True

    def notify_order(self, order):
        if order.status == order.Completed:
            buysell = 'BUY ' if order.isbuy() else 'SELL'
            txt = '{} {}@{}'.format(buysell, order.executed.size,
                                    order.executed.price)
            #print(txt)
    def next(self):
        for i, d in enumerate(self.datas):
            pos = self.getposition(d).size
            if (d.datetime.time().hour == 1):
                self.gridPoints=[]
                currentOpen = d.open[0]
                tickDiff = self.p.gridSize
                for i in range(7):
                    self.gridPoints.append(currentOpen*(1+(self.p.gridSize / currentOpen)))
                    self.buyline.lines.priceline[0] = currentOpen*(1+(self.p.gridSize / currentOpen))
                    tickDiff += self.p.gridSize
                tickDiff = self.p.gridSize
                for i in range(7):
                    self.gridPoints.append(currentOpen/(1+(self.p.gridSize / currentOpen)))
                    self.buyline.lines.priceline[0] = currentOpen/(1+(self.p.gridSize / currentOpen))
                    tickDiff += self.p.gridSize
            if (d.datetime.date().weekday() == 3): #Only trade Wednesdays
                if not pos:  # not in the market
                    for point in self.gridPoints:
                        if d.close[-1] < point and d.close[0] > point and d.datetime.time().hour < 23:       
                            self.buyline.lines.priceline[0] = point
                            self.buy(size=0.001)  # enter long
                            break
                else:
                    #Sell on market close if we are position
                    if (d.datetime.time().hour >= 23):
                        self.close(data=d,size=0.001)
                    for point in self.gridPoints:
                        if d.close[-1] > point and d.close[0] < point:
                            self.buyline.lines.priceline[0] = point
                            self.close(size=0.001)  # exit
                            break

class GridBot(bt.Cerebro): 
    def start(self):
        realtime=False
        cerebro = bt.Cerebro(tz=pytz.timezone('US/Eastern'))


        # Add the strategy
        cerebro.addstrategy(GridBotStrategy)

        # Create our store
        config = {'apiKey': 'apikeyHere',
                    'secret': 'secretHere',
                    'password':'passwordHere'
                    }


        # IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
        # for get cash or value if You have never held any BNB coins in your account.
        # So switch BNB to a coin you have funded previously if you get errors
        store = CCXTStore(exchange='coinbasepro', currency='BTC', config=config, retries=5, debug=False)


        # Get the broker and pass any kwargs if needed.
        # ----------------------------------------------
        # Broker mappings have been added since some exchanges expect different values
        # to the defaults. Case in point, Kraken vs Bitmex. NOTE: Broker mappings are not
        # required if the broker uses the same values as the defaults in CCXTBroker.
        broker_mapping = {
            'order_types': {
                bt.Order.Market: 'market',
                bt.Order.Limit: 'limit',
                bt.Order.Stop: 'stop-loss', #stop-loss for kraken, stop for bitmex
                bt.Order.StopLimit: 'stop limit'
            },
            'mappings':{
                'closed_order':{
                    'key': 'status',
                    'value':'closed'
                },
                'canceled_order':{
                    'key': 'result',
                    'value':1}
            }
        }

        cerebro.addanalyzer(RecorderAnalyzer)
        cerebro.addanalyzer(BacktraderPlottingLive,barup='green', volume=False, lookback=100)
        # Get our data
        # Drop newest will prevent us from loading partial data from incomplete candles
        hist_start_date = datetime.datetime.utcnow() - timedelta(days=28)
        print(realtime)
        if realtime:
            broker = store.getbroker(broker_mapping=broker_mapping)
            cerebro.broker.setcash(1000)
            cerebro.setbroker(broker)
            webbrowser.open('http://localhost:80', new=0)
            data = store.getdata(dataname='BTC/USDC', name="BTCUSDC",
                                    timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date,
                                    compression=60, ohlcv_limit=300,historical=False,live=True,backfill_start=False)
        else:
            broker = store.getbroker(broker_mapping=broker_mapping)
            cerebro.broker.setcash(1000)
            cerebro.setbroker(broker)
            data = store.getdata(dataname='BTC/USDC', name="BTCUSDC",
                                    timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date, todate=datetime.datetime.utcnow(),
                                    compression=60, ohlcv_limit=300,historical=True)
        # Add the feed
        cerebro.replaydata(data,timeframe=bt.TimeFrame.Minutes,compression=60)

        # Run the strategy
        cerebro.run(tz=pytz.timezone('US/Eastern'))
        if not realtime:
            p = BacktraderPlotting(style='bar',barup='green',volume=False, lookback=200)
            cerebro.plot(p,tz=pytz.timezone('US/Eastern'))
    def __init__(self):
        try:
            self.start()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            tb = traceback.format_exc()
            print(tb)
            print(str(e))
if __name__ == "__main__":
    try:
        GridBot()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print(str(e))