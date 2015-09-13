from __future__ import (absolute_import, division, print_function,
						unicode_literals)
#from src.backtrader_indicator_decisions import Decision
from src.stock import Stock, str2date 
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt

# Create a Stratey
class TestStrategy(bt.Strategy):
	params = (
		('maperiod', 15),
		('stake', 10),
	)

	def log(self, txt, dt=None):
		''' Logging function fot this strategy'''
		dt = dt or self.datas[0].datetime.date(0)
		print('%s, %s' % (dt.isoformat(), txt))

	def __init__(self):
		# Keep a reference to the "close" line in the data[0] dataseries
		self.dataclose = self.datas[0].close

		# Set the sizer stake from the params
		self.sizer.setsizing(self.params.stake)

		# To keep track of pending orders and buy price/commission
		self.order = None
		self.buyprice = None
		self.buycomm = None

		# Add a MovingAverageSimple indicator
		self.sma = bt.indicators.SimpleMovingAverage(
			self.datas[0], period=self.params.maperiod)

		self.sma5 = bt.indicators.SimpleMovingAverage(
			self.datas[0], period=5)
		self.sma10 = bt.indicators.SimpleMovingAverage(
			self.datas[0], period=10)
		self.sma15 = bt.indicators.SimpleMovingAverage(
			self.datas[0], period=15)

		# Indicators for the plotting show
		bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
		bt.indicators.WeightedMovingAverage(self.datas[0], period=25,
											subplot=True)
		bt.indicators.StochasticSlow(self.datas[0])

		self.macd = bt.indicators.MACDHisto(self.datas[0])

		rsi = bt.indicators.RSI(self.datas[0])
		bt.indicators.SmoothedMovingAverage(rsi, period=10)
		bt.indicators.ATR(self.datas[0], plot=False)

	def notify_order(self, order):
		if order.status in [order.Submitted, order.Accepted]:
			# Buy/Sell order submitted/accepted to/by broker - Nothing to do
			return

		# Check if an order has been completed
		# Attention: broker could reject order if not enougth cash
		if order.status in [order.Completed, order.Canceled, order.Margin]:
			if order.isbuy():
				self.log(
					'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
					(order.executed.price,
					 order.executed.value,
					 order.executed.comm))

				self.buyprice = order.executed.price
				self.buycomm = order.executed.comm
			else:  # Sell
				self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
						 (order.executed.price,
						  order.executed.value,
						  order.executed.comm))

			self.bar_executed = len(self)

		# Write down: no pending order
		self.order = None

	def notify_trade(self, trade):
		if not trade.isclosed:
			return

		self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
				 (trade.pnl, trade.pnlcomm))

	def next(self):
		# Simply log the closing price of the series from the reference
		self.log('Close, %.2f' % self.dataclose[0])

		# Check if an order is pending ... if yes, we cannot send a 2nd one
		if self.order:
			return

	
		# Check if we are in the market
		if not self.position:

			# Not yet ... we MIGHT BUY if ...
			if self.macd.macd > self.macd.signal:

				# BUY, BUY, BUY!!! (with all possible default parameters)
				self.log('BUY CREATE, %.2f' % self.dataclose[0])

				# Keep track of the created order to avoid a 2nd order
				self.order = self.buy(size=100)

		else:

			if self.macd.macd > self.macd.signal and self.macd.macd[0] < self.macd.macd[-1]:
				# SELL, SELL, SELL!!! (with all possible default parameters)
				self.log('SELL CREATE, %.2f' % self.dataclose[0])

				# Keep track of the created order to avoid a 2nd order
				self.order = self.sell(size=100)


def get_datapath(start, end ):
	try:
		s = Stock(sys.argv[1]) 
	except:
		print('Need to provide Stock symbol as an argument')
		sys.exit(1)

	return s.range2csv(start, end)

def get_start_end():
	if len(sys.argv) >= 3:
		start = str2date(sys.argv[2])
		print('using user start:', start)
	else:
		start = datetime.datetime(2014, 1 , 24)
		print('using default start:', start)

	if len(sys.argv) >= 4:
		end = str2date(sys.argv[3])
		print('using user end:', end)
	else:
		end = datetime.datetime.now()
		print('using default end:', end)
	return start, end 


if __name__ == '__main__':
	# Create a cerebro entity
	cerebro = bt.Cerebro()
   # print 1
	# Add a strategy
	cerebro.addstrategy(TestStrategy)
	#print 2
	# Datas are in a subfolder of the samples. Need to find where the script is
	# because it could have been called from anywhere
	
	#modpath = os.path.dirname(os.path.abspath(sys.argv[0]))

	start, end = get_start_end()	
	datapath = get_datapath(start, end)

	# Create a Data Feed
	data = bt.feeds.YahooFinanceCSVData(
		dataname=datapath,
		# Do not pass values before this date
		fromdate=start,
		# Do not pass values before this date
		todate=end	,
		# Do not pass values after this date
		reverse=False)
	#print 3
	# Add the Data Feed to Cerebro
	cerebro.adddata(data)
	#print 4
	# Set our desired cash start
	cerebro.broker.setcash(10000.0)

	# Set the commission
	cerebro.broker.setcommission(commission=0.05)

	# Print out the starting conditions
	print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

	# Run over everything
	cerebro.run()
	# Print out the final result
	print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

	# Plot the result
	cerebro.plot()