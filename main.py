import requests
import bs4
import threading
import re
import RandomHeaders
import random
import csv
import time
import os

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
#AMAZON_URL = "https://www.amazon.com/s/search-alias%3Dtradein-aps&field-keywords={0}&page={1}"
AMAZON_URL = "https://www.amazon.com/s/ref=sr_nr_i_0?srs=9187220011&fst=as%3Aoff&rh=i%3Atradein-aps%2Ck%3A{0}%2Ci%3Astripbooks&page={1}"
USED_PRICE_URL = "https://www.amazon.com/gp/offer-listing/{0}/ref=dp_olp_used?ie=UTF8&condition=used"
ALL_PAGE = "https://www.amazon.com/gp/offer-listing/{0}/ref=olp_f_new?ie=UTF8&f_all=true&f_new=true&f_used=true"
ITEM_SELECTOR = ".s-item-container"
TRADE_IN_SELECTOR = ".a-color-price"
ITEM_SPECIFICS = ".a-text-left.a-col-right"
# Page count = [0], Publisher = [1], ISBN-100 = [2], ISBN-13 = [3]
BOOK_TITLE = ".s-access-title"
BOOK_COVER = ".cfMarker"
TRADE_IN_REVIEW_BOX = ".a-span-last"
THREADS = 10

try:
	proxy = open("proxyAddress.txt").readlines()
	proxy = [p.rstrip('\n') for p in proxy]
except:
	raise Exception("Proxy not defined")

proxyStatus = {}

def chunks(l, n):
	for i in range(0, len(l), n):
		yield l[i:i + n]

def isTradeInEligible(item):
	# Determines if the item is trade in eligible or not
	return ('tradein' in item.select(TRADE_IN_REVIEW_BOX)[0])

def extractAllPageInfo(asin):
	for i in range(3):
		try:
			info = {}
			url = ALL_PAGE.format(asin)
			page = grabPage(url)
			offer = page.select(".olpOffer")[0]
			try:
				info['comment'] = offer.select('.expandedNote')[0].getText().strip().partition("\n")[0][:75]
			except:
				try:
					info['comment'] = offer.select(".comments")[0].getText().strip().partition("\n")[0][:75]
				except:
					info['comment'] = ""
			info['price'] = round(float(offer.select(".olpOfferPrice")[0].getText().replace("$", "")), 2)
			try:
				shipping = round(float(offer.select(".olpShippingPrice")[0].getText().replace("$", "")), 2)
			except:
				shipping = 0
			info['shipping'] = shipping
			info['total'] = info['price'] + shipping
			info['sellerName'] = offer.select(".olpSellerName")[0].getText().strip()
			sellerColumn = offer.select(".olpSellerColumn")
			info['percentRating'] = sellerColumn[0].select("b")[0].getText().strip()
			info['totalRatings'] = int(''.join(re.findall("\d+", str(sellerColumn[0].select(".a-spacing-small")[0].getText()).partition("(")[2].partition(")")[0])))
			info['arrivalDate'] = offer.select(".a-expander-partial-collapse-content")[0].getText().strip()
			info['condition'] = offer.select(".olpCondition")[0].getText().strip().replace("  ", "").replace("\n", " ")
			info['title'] = page.select("#olpProductDetails .a-spacing-none")[0].getText().strip().replace("  ", "").replace("\n", " ")
			info['id'] = asin
			info['book_reviews'] = int(page.select(".a-size-small .a-link-normal")[0].getText().partition("   ")[2].partition(" c")[0])
			info['author'] = page.select("#olpProductByline")[0].getText().partition('by')[2].partition('\n')[0]
			info['book_review_star'] = float(page.select(".a-icon-alt")[0].getText().partition(" ")[0])
			info['profit'] = ""
			info['url'] = "https://www.amazon.com/dp/{}".format(asin)
			for val in page.select("img"):
				if 'return to' in str(val).lower():
					try:
						info['book_cover_image'] = str(val).partition('src="')[2].partition('"')[0]
						break
					except:
						info['book_cover_image'] = ""
			return info
		except:
			pass
	return None

# take BeautifulSoup object and return the number of pages that can be searched
def getPageCount(page):
	try:
		pageCount = int(soup.find_all("li", {"class" : "a-disabled"})[-1].getText())
	except:
		try:
			pageCount = int(re.findall("(\d+)", str(page.select("#pagn")[0].getText().replace("\n", " ")))[-1])
		except:
			pageCount = 1
	return pageCount

# take the id of the item that you want and return the price of the product
def extractPrice(itemID):
	try:
		page = grabPage(USED_PRICE_URL.format(itemID))
		offer = page.select(".olpOffer")[0]
		price = float(offer.select(".olpOfferPrice")[0].getText().replace("$", ""))
		try:
			shipping = float(offer.select(".olpShippingPrice")[0].getText().replace("$", ""))
		except:
			shipping = 0
		return price + shipping
	except:
		print("Error returning 1000...")
		return 1000

def grabPage(url):
	for i in range(10):
		proxies = {"http": random.choice(proxy), "https": random.choice(proxy)}
		try:
			res = requests.get(url, headers=RandomHeaders.LoadHeader(), proxies=proxies, timeout=10)
		except Exception as exp:
			res = None
		if res != None:
			break
	page = bs4.BeautifulSoup(res.text, 'lxml')
	try:
		pageNum = re.findall('page\S(\d+)', url)[0]
	except:
		pageNum = 1
	print("Grabbed: {} | Page: {}".format(page.title.string, pageNum))
	return page

def extractInfoFromItem(item):
	print("extractInfoFromItem")
	try:
		tempInfo = {}
		tempInfo['title'] = item.select(BOOK_TITLE)[0].getText()
		tempInfo['item_id'] = str(item.select(".s-access-detail-page")[0]).partition('/dp/')[2].partition("/")[0]
		tempInfo['item_url'] = "https://www.amazon.com/dp/" + tempInfo['item_id']
		tempInfo['cover'] = str(item.select(BOOK_COVER)[0]).partition('src="')[2].partition('"')[0]
		tempInfo['page_count'] = item.select(ITEM_SPECIFICS)[0].getText()
		tempInfo['publisher'] = item.select(ITEM_SPECIFICS)[1].getText()
		tempInfo['isbn_100'] = item.select(ITEM_SPECIFICS)[2].getText()
		tempInfo['isbn_13'] = item.select(ITEM_SPECIFICS)[3].getText()
		tempInfo['trade_in_price'] = float(item.select(TRADE_IN_SELECTOR)[0].getText().replace('$', ''))
	except:
		tempInfo = None
	print("TEMPINFO {}".format(tempInfo))
	return tempInfo

def extractInfoFromPage(page):
	print("extractInfoFromPage")
	pageItems = []
	for item in page.select(ITEM_SELECTOR):
		info = extractInfoFromItem(item)
		if info != None:
			print(info)
			pageItems.append(info)
	return pageItems

def extractInfoFromURL(url):
	page = grabPage(url)
	return extractInfoFromPage(page)

def genURLs(keyword, pageCount):
	urlList = []
	for i in range(1, pageCount+1):
		url = AMAZON_URL.format(keyword, i)
		urlList.append(url)
	return urlList

# search class to parse the amazon webpages
class search(object):
	def __init__(self):
		self.toSearch = []
		self.results = []
		self.profitable = []

	# add the textbook information given a search tearm
	# will populate a list of url's to query
	def add(self, keyword):
		url = AMAZON_URL.format(keyword, 1)
		page = grabPage(url)
		pageCount = getPageCount(page)
		print("Keyword: {} Pages: {}".format(keyword, pageCount))
		for url in genURLs(keyword, pageCount):
			self.toSearch.append(url)

	# extract all of the page info given a list of urls
	def extractFromURL(self, urlList):

		print(urlList)

		# go through every url in the list and append profitable finds
		for url in urlList:
			info = extractInfoFromURL(url)
			for val in info:
				val['purchase_price'] = extractPrice(val['item_id'])
				self.results.append(val)
				print(val)
				if val['purchase_price'] < val['trade_in_price']:
					self.profitable.append(val)
					print("Profitable item found")

	def start(self):

		parts = int(len(self.toSearch)/THREADS)

		if parts != 0:
			listOfURLs = chunks(self.toSearch, parts)
		else:
			listOfURLs = chunks(self.toSearch, 1)

		threads = [threading.Thread(target=self.extractFromURL, args=(url[0],)) for url in listOfURLs]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join()
		return self.results

class amazonTextbookDB(object):
	def __init__(self, arg):
		self.arg = arg
		self.database = []

	def search(self, keyword):
		url = AMAZON_URL.format(keyword, 1)
		page = grabPage(url)
		pageCount = getPageCount(page)
		print("Keyword: {} Pages: {}".format(keyword, pageCount))
		for i in range(1, pageCount):
			if i != 1:
				url = AMAZON_URL.format(keyword, i)
				page = grabPage(url)


if __name__ == '__main__':

	e = search()

	# e.add(raw_input("Search Term: "))
	e.start()
	print("{} Profitable items found".format(len(e.profitable)))
	for val in e.profitable:
		print("{} - ${}".format(val['item_url'],  val['trade_in_price'] - val['purchase_price']))
	start_time = time.clock()
	e = search()

	e.add('biology')
	e.add('chemistry')
	e.add('psychology')
	e.add('philosophy')
	e.add('education')
	e.add('textbook')
	e.add('computer')
	e.start()

	AllNewsInfo = []
	t = random.choice(list(e.profitable))['item_id']
	AllNewsInfo.append(list(extractAllPageInfo(t).keys()))

	for val in e.profitable:
		try:
			tInfo = extractAllPageInfo(val['item_id'])
			if tInfo != None:
				tInfo['profit'] = round(float(val['trade_in_price']), 2) - round(float(val['purchase_price']), 2)
				AllNewsInfo.append(list(tInfo.values()))
				print("appended")
		except Exception as exp:
			print(exp)
	with open('info.csv', 'wb') as myfile:
		wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
		wr.writerows(AllNewsInfo)
	timeSeconds = round(float(time.clock() - start_time), 2)
	subject = "{} Profitable Items found in {} Seconds".format(len(AllNewsInfo), timeSeconds)
	try:
		import sendText
		sendText.sendText(subject)
		import sendEmail
		sendEmail.sendToMe(subject)
	except:
		try:
			sendText.sendText("Error on Send Email")
		except:
			pass
