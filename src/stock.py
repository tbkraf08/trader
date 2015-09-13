


from googlefinance import getQuotes
from yahoo_finance import Share
from dateutil.parser import parse
import datetime
import csv
import os 

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MONGO_DB = 'tomastocks'

GOOGLE_TYPE = 'goog'
GOOGLE_FINAL_PRICE_FIELD = 'LastTradePrice'
GOOGLE_DATE_FIELD = 'LastTradeDateTime'
GOOGLE_DIVIDEND_FIELD = 'Dividend'
GOOGLE_YIELD_FIELD = 'Yield'
GOOGLE_ID_FIELD = 'ID'

YAHOO_TYPE = 'yhoo'
YAHOO_FINAL_PRICE_FILED = 'Close'
YAHOO_OPEN_FIELD = 'Open'
YAHOO_HIGH_FIELD = 'High'
YAHOO_LOW_FIELD = 'Low'
YAHOO_VOLUME_FIELD = 'Volume'
YAHOO_DATE_FIELD = 'Date'
YAHOO_ADJ_CLOSE_FIELD = 'Adj_Close'

ONE_MINUTE = 1
ONE_DAY = 1440
ONE_YEAR = 365

DATE_FORMAT = "%Y-%m-%d"

def str2date(date):
	try:
		if isinstance(date, datetime.datetime):
			return date
		elif isinstance(date, str) or isinstance(date, unicode):
			return parse(date)
		elif isinstance(date, int) or isinstance(date, long):
			return datetime.datetime.fromtimestamp(date)
		else:
			logger.error('Date is not in parseable format')
			raise Exception("Date is not in a parseable format: %s", date)
	except:
		logger.error('Error parsing date: %s', date)
		raise Exception("Issue parsing date: %s", date)

def date2str(date, _format=DATE_FORMAT):
	if isinstance(date, datetime.datetime):
		return date.strftime(_format)
	elif isinstance(date, str) or isinstance(date, unicode):
		return date2str(str2date(date))
	else:
		raise Exception("Date is not a datetime object")

class Stock:
	'''
		class for a stock that will hold information about the stock price
		will also handle pulling data from ticker api and maintaining info
		in db to avoid network calls
	'''
	SBL = None # symbol
	GOBJ = None # google stock object 
	YOBJ = None # yahoo stock object
	def __init__(self, symbol):
		
		self.logger = logging.getLogger(Stock.__name__)
		self.SBL = symbol
		
	def fetch(self):
		self.logger.info('fetch starting: %s', self.SBL)
		'''
			find the most recent price of the symbol
		'''	
		try:
			x = getQuotes(self.SBL)[0]

			# 1 = 1 min interval, This is a fetch of the current price. Not sure how often can hit api 
			# so going to fetch every miniute 
			self.GOBJ = Tick(ONE_MINUTE, self.SBL, x[GOOGLE_FINAL_PRICE_FIELD], x[GOOGLE_DATE_FIELD], dividend=x[GOOGLE_DIVIDEND_FIELD], 
									_id=x[GOOGLE_ID_FIELD], _yield=x[GOOGLE_YIELD_FIELD], _type=GOOGLE_TYPE)
		except:
			self.GOBJ = None
			self.logger.warn('issue fetching for: %s', self.SBL)

		self.logger.info('fetch complete: %s', self.GOBJ)
		return self.GOBJ

	def fetch_history(self, start=None, end=None):
		self.logger.info('fetching history start: %s', self.SBL)
		'''
			find historical price of the symbol between
			start and end date. default is past two weeks
			# start and end can be a datetime or a string 
		'''
		start, end = self._get_fetch_range(start, end)
		yahoo = self._get_yahoo_obj()

		try:
			history = []
			for x in yahoo.get_historical(start, end):
				# 1440 = 1 day interval
				x = Tick(ONE_DAY, self.SBL, x[YAHOO_FINAL_PRICE_FILED], x[YAHOO_DATE_FIELD], _open=x[YAHOO_OPEN_FIELD], high=x[YAHOO_HIGH_FIELD], low=x[YAHOO_LOW_FIELD], volume=x[YAHOO_VOLUME_FIELD], adj_close=x[YAHOO_ADJ_CLOSE_FIELD], _type=YAHOO_TYPE)
				
				history.append(x)
		
		except:
			self.logger.warn('issue fetching history for: %s', self.SBL)
			history = []

		self.logger.info('fetching history complete: %s  retrieved rows', len(history))
		return history

	def range2csv(self, start=None, end=None):
		self.logger.info('start range to csv')
		'''
			put range of data in csv format for backtrader
		'''
		start,end = self._get_fetch_range(start, end)
		file_name = self._gen_file_name(start, end)

		if not os.path.isfile(file_name):
			self.logger.info('creating csv file')
			with open(file_name, 'w') as f:
				writer = csv.writer(f)

				data = self.fetch_history()
				data.reverse()

				writer.writerow(data[0].to_csv(header=True))

				for d in data:
					writer.writerow(d.to_csv())
		else:
			self.logger.info('file created already')
	
		self.logger.info('done with range to csv: %s', file_name)
		return file_name

	def _get_fetch_range(self, start, end):
		if not end:
			end = datetime.datetime.now()
		else:
			end = str2date(end)

		if not start:
			start = end - datetime.timedelta(days=ONE_YEAR)
		
		start = str2date(start)
		start = start.strftime(DATE_FORMAT)
		end = end.strftime(DATE_FORMAT)
		return start, end

	def _gen_file_name(self, start, end, postfix='txt'):
		_dir = 'data/%s' % (self.SBL)

		try:
		    os.stat(_dir)
		except:
		    os.mkdir(_dir) 

		return '%s/%s_%s_to_%s.%s' % (_dir, self.SBL, start, end, postfix)

	def _get_yahoo_obj(self):
		'''
 			helper class to get yahoo quote for stock symbol
 			(yahoo has more functionality then google)
 		'''
		if not self.YOBJ:
			self.logger.info('getting yahoo stock object')
			try:
				self.YOBJ = Share(self.SBL)
			except:
				self.logger.error('issue getting yahoo stock object for: %s', self.SBL)
				raise Exception('No yahoo stock quote for: %s', self.SBL)

		return self.YOBJ


class MongoStock(Stock):
	'''
		takes the fun of the Stock class 
		and handles the logic for adding new data to mongo
		while checking to see if it exists locally
	'''
	DB = None
	def __init__(self, *args, **kwargs):
		Stock.__init__(self, *args, **kwargs)
		if 'db' in kwargs:
			self.DB = kwargs['db']
		else:
			self.DB = MONGO_DB

	def add_stock(self, doc):
		'''
			put stock ticker in mongo 
		'''
		pass

	def add_stocks(self, docs):
		for i in docs:
			self.add_stocks(i)

	def is_data(self, start, end):
		'''
			checks if there is ticker data in mongo for given range
			return FULL COVERAGE | RANGE TO QUERY FOR | NONE
		'''
		pass
	

class Tick:
	'''
		class for a stocks tick event
		can be at various intervals
	'''
	INTERVAL = None 
	FINAL_PRICE = None
	SYMBOL = None
	DATE = None
	TYPE = None
	OPEN = None # yahoo specific
	HIGH = None # yahoo specific
	LOW = None # yahoo specific
	VOLUME = None # yahoo specific
	ADJ_CLOSE = None # yahoo specific
	DIVIDEND = None # google finance specific
	YIELD = None # google finance specific
	ID = None # google finance specific
	def __init__(self, interval, symbol, close, date, _open=None, high=None, low=None, volume=None, adj_close=None, dividend=None, _yield=None, _id=None, _type=None):
		self.INTERVAL, self.SYMBOL, self.OPEN, self.CLOSE, self.HIGH, self.LOW, self.DATE, self.VOLUME, self.ADJ_CLOSE, self.DIVIDEND, self.YIELD, self.ID, self.TYPE =  interval,      symbol,     _open,      close,      high,      low,      date,      volume,      adj_close,         dividend,     _yield,     _id, 	_type

		self.DATE = str2date(self.DATE)

	def to_dict(self):
		return {
			'interval': self.INTERVAL,
			'symbol': self.SYMBOL,
			'open': self.OPEN,
			'close': self.CLOSE,
			'high': self.HIGH,
			'low': self.LOW,
			'date': self.DATE,
			'volume': self.VOLUME,
			'adj_close': self.ADJ_CLOSE,
			'dividend': self.DIVIDEND,
			'yield': self.YIELD,
			'id': self.ID,
			'type': self.TYPE,
		}

	def to_csv(self, header=False):
		if header:
			return ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']

		return [date2str(self.DATE), self.OPEN, self.HIGH, self.LOW, self.CLOSE, self.VOLUME, self.ADJ_CLOSE]

	def __str__(self):
		return '%s' % (self.to_dict())

Stock.__name__ = 'Stock'
MongoStock.__name__ = 'MongoStock'
Tick.__name__ = 'Tick'

if __name__ == "__main__":
    s = MongoStock('UWTI')
    #s.fetch()
    #s.fetch_history()
    s.range2csv()





