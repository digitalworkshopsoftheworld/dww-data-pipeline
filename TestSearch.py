import imdb

i = imdb.IMDb()
companyList = i.search_company('weta digital')

for company in companyList:
	print company['name']
