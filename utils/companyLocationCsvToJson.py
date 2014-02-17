# 
# Company Location mapper.
# 
# Takes a csv containing locations for every company and a location region index and
# merges them into a company map file.
#
# Usage: {company_locations}.csv, {region_index}.csv, {company_map}.json) 

import json
import csv
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

if len(sys.argv) < 3:
    print("Usage: {company_locations}.csv, {region_index}.csv, {company_map}.json)")
    sys.exit(1)

companyLocations = {}
regionIndex = {}
companyMapMerged = None

#Open CSV location file
try:
    with open(sys.argv[1], 'rb') as csvfile:
        csvRead = csv.reader(csvfile, delimiter=',')
        for row in csvRead:
            if row[1]:
                companyLocations[row[0]] = {"geoLoc": row[1], "region": row[3]}
except IOError:
    print "No company location csv found."

#Open region index file
try:
    with open(sys.argv[2], 'rb') as regionIndexFile:
        csvRead = csv.reader(regionIndexFile, delimiter=',')
        for row in csvRead:
            regionIndex[row[0]] = row[1]
except IOError:
    print "No location index csv found."


# Open company map
try:
    with open(sys.argv[3], 'rb') as companyMapFile:
        companyMap = json.load(companyMapFile)

        reverseMap = {}
        for cName, cObj in companyMap['maps'].iteritems():
            reverseMap[cObj['name']] = {'region':'', 'geoLoc':''}

        for companyName, companyObj in reverseMap.iteritems():
            if companyName in companyLocations:
                companyObj['geoLoc'] = companyLocations[companyName]['geoLoc']
                companyObj['region'] = companyLocations[companyName]['region']
except IOError:
    print "No company map file found"

companyMapMerged = {'maptype': companyMap['maptype'],  'locations': reverseMap, 'maps': companyMap['maps'], 'regions':regionIndex}
print json.dumps(companyMapMerged, ensure_ascii=False).encode('utf8')

