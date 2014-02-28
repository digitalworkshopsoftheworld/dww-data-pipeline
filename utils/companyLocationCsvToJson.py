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
    print("Usage: {company_locations}.csv, {region_index}.csv, {global_region_index}.csv, {company_map}.json)")
    sys.exit(1)

companyLocations = {}
regionIndex = {}
globalRegionIndex = {}
companyMapMerged = None

#Open CSV location file
try:
    with open(sys.argv[1], 'rb') as csvfile:
        csvRead = csv.reader(csvfile, delimiter=',')
        headers = csvRead.next()
        for row in csvRead:
            if row[1]:
                companyLocations[row[0]] = {"geoLoc": row[1], "region": row[3].lower()}
except IOError:
    print "No company location csv found."

#Open region index file
try:
    with open(sys.argv[2], 'rb') as regionIndexFile:
        csvRead = csv.reader(regionIndexFile, delimiter=',')
        headers = csvRead.next()
        for row in csvRead:
            regionIndex[row[0].lower()] = {'geoLoc':row[2], 'globalRegion':row[1].lower()};
except IOError:
    print "No location index csv found."


#Open global region index file
try:
    with open(sys.argv[3], 'rb') as globalRegionIndexFile:
        csvRead = csv.reader(globalRegionIndexFile, delimiter=',')
        headers = csvRead.next()
        for row in csvRead:
            globalRegionIndex[row[0]] = row[1].lower()
except IOError:
    print "No global location index csv found."


# Open company map
try:
    with open(sys.argv[4], 'rb') as companyMapFile:
        companyMap = json.load(companyMapFile)

        reverseMap = {}
        for cName, cObj in companyMap['maps'].iteritems():
            reverseMap[cObj['name']] = {'location':'', 'geoLoc':''}

        for companyName, companyObj in reverseMap.iteritems():
            if companyName in companyLocations:
                companyObj['geoLoc'] = companyLocations[companyName]['geoLoc']
                companyObj['location'] = companyLocations[companyName]['region'].lower()
except IOError:
    print "No company map file found"

companyMapMerged = {'maptype': companyMap['maptype'],  'locations': reverseMap, 'maps': companyMap['maps'], 'regions':regionIndex, 'globalRegions': globalRegionIndex}
print json.dumps(companyMapMerged, ensure_ascii=False).encode('utf8')

