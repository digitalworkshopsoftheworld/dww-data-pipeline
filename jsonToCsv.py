import json
import csv
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

if len(sys.argv) < 3:
    print("Usage: in.json, out.csv")
    sys.exit(1)

inFile = open(sys.argv[1])
inData = json.load(inFile)
inFile.close()

outFile = csv.writer(open(sys.argv[2], "wb+"))
outFile.writerow(
    ["personId", "personName", "imdbMovieId", "companySearch", "companyMatchRatio",
                 "personRole", "movieReleaseYear", "matchedCompanyId", "matchedCompanyName"])


for line in inData['data']:
    # Get stuff
    outFile.writerow([str(line[0]['data']['id']),
                     str(line[0]['data']['name']),
                     str(line[1]['data']['movieID']),
                     str(line[1]['data']['company']),
                     str(line[1]['data']['matchRatio']),
                     str(line[1]['data']['role']),
                     str(line[1]['data']['release']),
                     str(line[2]['data']['id']),
                     str(line[2]['data']['name'])
                      ])

print(str(len(inData['data'])) + " entries written")
