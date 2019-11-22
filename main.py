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
ITEM_SELECTOR = ".sg-col-inner"
TRADE_IN_SELECTOR = ".a-color-price"
ITEM_SPECIFICS = ".a-text-left.a-col-right"
# Page count = [0], Publisher = [1], ISBN-100 = [2], ISBN-13 = [3]
BOOK_TITLE = "a-size-medium a-color-base a-text-normal"
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
		print("PAGE COUNT:\t{}".format(pageCount))
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

# populates the responses list with request responses from url
def makeRequest(url, responses):
	proxies = {"http": random.choice(proxy), "https": random.choice(proxy)}
	try:

		response = requests.get(url, headers=RandomHeaders.LoadHeader(), proxies=proxies, timeout=10)
		responses.append(response.text)

	except Exception as e:
		pass

# given a url return the page information
def grabPage(url):

	print("GRABBING: \t{}".format(url))
	responses = []

	# thread 5 requests to the url
	threads = [threading.Thread(target=makeRequest, args=(url, responses,)) for i in range(0,5)]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()

	print("LENGTH {}".format(len(responses)))

	# return the first response that yields a valid page
	for response in responses:
		if response != None:

			page = bs4.BeautifulSoup(response, 'lxml')
			break
		else:
			pass
	try:
		pageNum = re.findall('page\S(\d+)', url)[0]
		print("Grabbed: {} | Page: {}".format(page.title.string, pageNum))
	except:
		pageNum = 1

	return page

# given an item pull all of the item information
def extractInfoFromItem(item):
	print("\n\n\n THIS IS MY ITEM \n\n\n{}".format(item))
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
	return tempInfo

# given page (bs4 object) return all items on that page
def extractInfoFromPage(page):

	pageItems = []

	for item in page.select(ITEM_SELECTOR):
		info = extractInfoFromItem(item)
		if info != None:
			print(info)
			pageItems.append(info)
	return pageItems

# queries url arg and returns the page info
def extractInfoFromURL(url):
	page = grabPage(url)
	return extractInfoFromPage(page)

# generate urls with the page number given the total number of pages for each keyword
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
		print('ADDING:\t{}'.format(keyword))
		url = AMAZON_URL.format(keyword, 1)
		page = grabPage(url)
		pageCount = getPageCount(page)
		print("Keyword: {} Pages: {}".format(keyword, pageCount))
		for url in genURLs(keyword, pageCount):
			self.toSearch.append(url)

	# extract all of the page info given a list of urls
	def extractFromURL(self, urlList):
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

	# start the search object
	def start(self):

		parts = int(len(self.toSearch)/THREADS)

		if parts != 0:
			listOfURLs = chunks(self.toSearch, parts)
		else:
			listOfURLs = chunks(self.toSearch, 1)

		threads = [threading.Thread(target=self.extractFromURL, args=(url,)) for url in listOfURLs]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join()

		return self.results

class amazonTextbookDB(object):
	def __init__(self, arg):
		self.arg = arg
		self.database = []

	# takes keyword and queries amazon for that textbook keyword
	def search(self, keyword):
		url = AMAZON_URL.format(keyword, 1)
		page = grabPage(url)
		pageCount = getPageCount(page)
		print("\n\n\nPAGE COUNT {}\n\n\n".format(pageCount))
		print("Keyword: {} Pages: {}".format(keyword, pageCount))
		for i in range(1, pageCount):
			if i != 1:
				url = AMAZON_URL.format(keyword, i)
				page = grabPage(url)


if __name__ == '__main__':

	# load the keywords to add to the query
	###### Will need to chunk this later or loop it
	try:
		keyWords = open("smallKeyWords.txt").readlines()
		keyWords = [word.rstrip('\n') for word in keyWords]
	except:
		raise Exception("Keywords not defined")

	e = search()

	threads = [threading.Thread(target=e.add, args=(keyword,)) for keyword in keyWords]

	for thread in threads:
		thread.start()
	for thread in threads:
		 thread.join()

	# start the searcher
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

	# write the price quotes to csv
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
