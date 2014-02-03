#!/usr/bin/env python

import sys
import re
import resource
import pdb
import os
import gc
import cPickle as pickle
import time
import shutil
import json
from optparse import OptionParser
from Utils import Logger
import calendar

reload(sys)
sys.setdefaultencoding("utf-8")

# Import the IMDbPY package.
try:
    import imdb
    from imdb import Movie, Person, Character, Company
    from py2neo import neo4j, node, rel
    from fuzzywuzzy import fuzz

except ImportError:
    print('Missing neo4j or imdbpy or fuzzywuzzy')
    sys.exit(1)


class ImdbScraper:

    def __init__(self):
        # Company whitelists
        self.cachedCompanySearches = {}
        self.companyWhitelist = {}
        self.companyMap = None
        self.roleMap = None

        # Test neo4j connection
        try:
            # Indexes
            self.companyIndex = neo4jHandle.get_or_create_index(
                neo4j.Node, "company")
            self.movieIndex = neo4jHandle.get_or_create_index(
                neo4j.Node, "movie")
            self.personIndex = neo4jHandle.get_or_create_index(
                neo4j.Node, "person")
            self.jumpIndex = neo4jHandle.get_or_create_index(
                neo4j.Node, "jump")
        except:
            print "No connection to neo4j"
            sys.exit(1)

    def InitIMDB(self):
        # IMDB interface
        self.i = imdb.IMDb()

    def SetRootCompany(self, companyID, companySearchTag):
        self.companyID = companyID
        self.companySearchTag = companySearchTag
        self.rootCompany = self.i.get_company(self.companyID)

        # List of companies for quick checking against existing companies
        self.companyList = [self.rootCompany]

    def GetPeopleInFilmography(self, filmographyDepth):
        print("Root company is '" + str(companyID) +
              "', search term is '" + str(companySearchTag) + "'")

        personList = {}

        rootCompanyDB = self.GetCachedListAndNode(self.rootCompany, "company")
        companyNode = rootCompanyDB[0]
        companyObj = rootCompanyDB[1]

        # Dummy movie list of first n movies
        movieList = []

        if(filmographyDepth < 0):
            filmographyDepth = len(
                companyObj['special effects companies'])

        for i in range(filmographyDepth):
            movieList.append(companyObj['special effects companies'][i])

        for movie in movieList:
            movDB = self.GetCachedListAndNode(movie, "movie", ["visual effects"], False, "release dates")
            movNode = movDB[0]
            movLists = movDB[1]
            vfxCrew = None
            if 'visual effects' in movLists:
                vfxCrew = movLists['visual effects']

            if(vfxCrew):
                movCompanyRelationship = list(
                    neo4jHandle.match(start_node=companyNode, end_node=movNode))
                if(len(movCompanyRelationship) < 1):
                    neo4jHandle.create(
                        rel(companyNode, "FILMOGRAPHY", movNode))

                for person in vfxCrew:
                    vfxRole = self.ParseCompanyFromPersonNotes(
                        person.notes, self.companySearchTag)
                    if(len(vfxRole.matchedTag) > 0):
                        personList[person.getID()] = person
                print("--- '" + movNode.get_properties()['name'] + "'. Scanned " + str(
                    len(vfxCrew)) + " people. Total found: " + str(len(personList)))

        print("--- Total unique employees found: " + str(len(personList)))
        Log.String('!!! Memory usage: %s (mb)' % str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000))
        return personList

    def ConnectPeopleToCompanies(self, personList):
        print("---------------------------------")
        self.ResetRelationships()

        self.personCount = 0
        self.personTotal = len(personList)

        print("Searching employee filmographies")
        for personID, person in personList.iteritems():
            startmem = resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss / 1000000

            personDB = self.GetCachedListAndNode(
                person, "person", ["visual effects", "notes"], False)
            personNode = personDB[0]
            person = personDB[1]

            if person['visual effects']:
                if len(person['visual effects']) < 1:
                    print(
                        " === " + str(person['name']) + " has no VFX filmography.")
                    print(person)
                    print(" === Skipping...")
                    continue

                for movie in person['visual effects']:
                    movDB = self.GetCachedListAndNode(
                        movie, "movie", ["visual effects"], False, "release dates")
                    movNode = movDB[0]
                    vfxCrew = movDB[1]['visual effects']

                    personInMovie = self.FindPersonInList(vfxCrew, personNode)
                    if personInMovie:
                        vfxRole = self.ParseCompanyFromPersonNotes(
                            personInMovie.notes)
                        existingCompany = None
                        companyIsMapped = False

                        # Load company from pre-downloaded company or from map list
                        if options.useCompanyMap:
                            if vfxRole.company in self.companyMap['maps']:
                                mappedCompanyName = self.companyMap['maps'][vfxRole.company]['name']
                                if 'zzz_baddata' in mappedCompanyName:
                                    print "Found mapped baddata. Ignoring company"
                                elif 'zzz_role' in mappedCompanyName:
                                    print "Found mapped role. Ignoring company"
                                else:
                                    existingCompany = Company.Company(
                                        companyID=self.companyMap['maps'][vfxRole.company]['id'], 
                                        myName=self.companyMap['maps'][vfxRole.company]['name'])
                                    companyIsMapped = True

                        # Only search for the company if the map or memory has no entry for the company
                        if not existingCompany:
                            if vfxRole.company in self.companyWhitelist:
                                existingCompany = self.companyWhitelist[vfxRole.company]
                            else:
                                if len(vfxRole.company) > 0:
                                    print("Searching for " + vfxRole.company)
                                    compList = self.i.search_company(
                                        vfxRole.company)
                                    if len(compList) > 0:
                                        existingCompany = compList[0]
                                        self.companyWhitelist[
                                            vfxRole.company] = existingCompany
                                    else:
                                        print(
                                            "No results found for '" + str(vfxRole.company) + "'")
                                        continue
                                else:
                                    print "Skipping role '" + str(vfxRole.role) + "', '" + str(vfxRole.company) + "'. No associated company"
                                    continue

                        if existingCompany:
                            # Company node and lists
                            compDB = self.GetCachedListAndNode(
                                existingCompany, "company")
                            compNode = compDB[0]
                            existingCompany = compDB[1]

                            # Keep a flag in the DB for mapped companies
                            compNode.update_properties({'isMapped':companyIsMapped, 'location':''})

                            print("Attach '" + str(personInMovie['name']) + "' to '" + 
                                str(compNode.get_properties()['name']) + "' for '" + str(vfxRole.role) + "'")
                            self.ConnectPersonToCompany(personNode, compNode, vfxRole, movNode, personInMovie.notes)
                        else:
                            print("No company called '" + str(vfxRole.company) + "' for " + str(personInMovie['name']) + "' under role '" + str(vfxRole.role) + "'")
                    else:
                        print("Couldn't find person in movie")
            else:
                print "No person filmography object"

            personList[personID] = None
            self.personCount += 1
            print("=== " + str(self.personCount) + "/" +
                  str(self.personTotal) + " people processed")
            Log.String('!!! Delta Memory usage: %s (mb)' %
                  str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000 - startmem))
            Log.String('!!! Total Memory usage: %s (mb)' %
                  str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000))

    def ConnectPersonToCompany(self, personNode, companyNode, vfxrole, movieNode, rawNotes=""):
        personCompanyRelationship = list(
            neo4jHandle.match(start_node=personNode, end_node=companyNode))

        # Use fuzzy matching to see if we need to flag this relationship as one
        # to check the company
        fuzzyCompanyMatch = fuzz.ratio(companyNode.get_properties()[
                                       'name'].lower().strip(), vfxrole.company.lower().strip())

        relExists = False
        # Check for preexisting relationships to company
        for personRel in personCompanyRelationship:
            if(personRel.get_properties()["movieID"] == movieNode.get_properties()['id']):
                relExists = True

        if not relExists:
            roleNode, =  neo4jHandle.create(
                rel(personNode, "WORKED_FOR", companyNode))
            roleNode.update_properties(
                {'role': vfxrole.role, 'company': vfxrole.company, 'movieID': movieNode.get_properties()['id'], 'release': movieNode.get_properties()['release'], 'matchRatio': fuzzyCompanyMatch, 'rawNotes': rawNotes})
        Log.String("Match ratio: " + str(fuzzyCompanyMatch) + ". CompRole: " + str(vfxrole.company.lower().strip())
                   + ". Node: " + str(companyNode.get_properties()['name'].lower().strip()))

    def GetCachedListAndNode(self, imdbObj, nodeType, listKey="", forceUpdate=False, optionalKey=""):
        cachedList = None
        cachedListPickle = None
        pickleFileName = str(
            imdbCacheDir + "/" + nodeType + "/" + str(imdbObj.getID()) + ".pkl")
        cachedNode = neo4jHandle.get_indexed_node(
            nodeType, "id", imdbObj.getID())

        if not cachedNode or forceUpdate:
            self.UpdateImdbObj(imdbObj)

            cachedList = {}
            if listKey:
                # Append all keys to the cached list that match
                Log.String(" * Caching " + nodeType + " '" + str(
                    imdbObj))
                for key in imdbObj.keys():
                    for searchKey in listKey:
                        if searchKey in key:
                            cachedList[searchKey] = imdbObj[key]
                        if searchKey == 'notes':
                            cachedList['notes'] = imdbObj.notes

            else:
                Log.String(
                    " * Caching " + nodeType + " '" + str(imdbObj) + "'")
                cachedList = imdbObj

            if cachedList:
                # Build DB node
                if not cachedNode:
                    cachedNode, = neo4jHandle.create(
                        node(id=str(imdbObj.getID())))
                cachedNode.add_labels(nodeType)

                # Set node properties
                nodeProperties = {}
                nodeIndex = None

                if(optionalKey):
                    self.i.update(imdbObj, optionalKey)

                if nodeType == "movie":
                    date = "none"
                    if imdbObj.has_key('release dates'):
                        date = self.ParseEarliestDate(imdbObj['release dates'])
                    elif imdbObj.has_key('year'):
                        date = imdbObj['year']
                    nodeProperties['release'] = date
                    nodeProperties['name'] = imdbObj['title']
                    nodeIndex = self.movieIndex
                elif nodeType == "person":
                    nodeProperties['name'] = imdbObj['name']
                    nodeIndex = self.personIndex
                elif nodeType == "company":
                    nodeProperties['name'] = imdbObj['name']
                    nodeIndex = self.companyIndex

                cachedNode.update_properties(nodeProperties)
                nodeIndex.add("id", cachedNode['id'], cachedNode)

                # Save key list into pickle file
                pickleFile = open(pickleFileName, 'wb')
                cachedListPickle = pickle.dump(cachedList, pickleFile)
                pickleFile.close()
                Log.String(" * ...done.")
        else:
            try:
                with open(pickleFileName, 'rb'):
                    Log.String(
                        " * Cache file exists for '" + str(imdbObj) + "'")
                    pickleFile = open(pickleFileName, 'rb')
                    Log.String(" * Loading " + str(nodeType) + " '" + str(
                        imdbObj) + "' from cache")
                    cachedList = pickle.load(pickleFile)
                    pickleFile.close()
            except IOError:
                Log.String(" * No pickle found, recreating cache")
                cachedNode.delete()
                del cachedNode
                rebuiltDB = self.GetCachedListAndNode(
                    imdbObj, nodeType, listKey, True)
                cachedNode = rebuiltDB[0]
                cachedList = rebuiltDB[1]

        return cachedNode, cachedList

    def UpdateImdbObj(self, imdbObj):
        while True:
            try:
                self.i.update(imdbObj)
            except imdb.IMDbDataAccessError:
                print("*** HTTP error. Redialing")
                continue
            break

    def ParseEarliestDate(self, dateList):
        outDate = ""
        for date in dateList:
            cleanDate = re.sub(r'\([^)]+\)|^[^::]*::', '', date).strip()
            splitDate = cleanDate.split(" ")
            if len(splitDate) == 3:
                day = splitDate[0]
                month = splitDate[1]
                year = splitDate[2]
                splitDate[0] = year
                splitDate[1] = str(list(calendar.month_name).index(splitDate[1]))
                splitDate[2] = day
                return "-".join(splitDate)
        return outDate

    def ParseCompanyFromPersonNotes(self, notes, companyTag=""):
        outRole = VFXRole()
        # Remove symbols
        filtered = re.sub(r'[!@#*$\(\)\\\[\]]', '', notes).lower()
        filtered = re.sub("\"", "\'", filtered)
        # Remove episode lists
        filtered = re.sub(
            r'(\w+)\s(\bepisodes),?(\s\w+)?(-\w+)?', '', filtered)
        # Remove alternate name credits and uncredited roles
        filtered = re.sub(r'\suncredited|\sas\s.*$', '', filtered)
        # Remove company types
        filtered = re.sub(r'(?:\sltd|\sinc)\.|(?:\sltd|\sinc)', '', filtered)
        filtered = filtered.strip()

        splitRole = []
        splitRole = filtered.split(":")

        role = ""
        comp = ""
        Log.String(
            str("Filtered: '" + str(filtered) + "'. Original: '" + str(notes) + "'"))
        if(len(splitRole) > 1):
            role = str(splitRole[0]).strip()
            comp = str(splitRole[1]).strip()
            splitComp = comp.split(' - ')
            if(len(companyTag) > 0):
                if comp.find(self.companySearchTag) > -1:
                    outRole.matchedTag = companyTag
            outRole.role = role
            splitCompDivision = splitComp[0].split(",")
            if(len(splitCompDivision) > 1):
                outRole.company = splitCompDivision[1]
                outRole.role += (", " + splitCompDivision[0].strip())
            else:
                outRole.company = splitCompDivision[0]
        else:
            outRole.role = role

        outRole.company = outRole.company.strip()
        outRole.role = outRole.role.strip()

        return outRole

    #
    # Find functions
    #
    def FindOrCreateCompanyNode(self, imdbCompany):
        companyNode = neo4jHandle.get_indexed_node(
            "company", "id", imdbCompany.getID())
        if not companyNode:
            Log.String("Couldn't find company node. Searched for '" +
                       str(imdbCompany['name']) + "'. Creating...")
            while True:
                try:
                    self.i.update(imdbCompany)
                except imdb.IMDbDataAccessError:
                    print("*** HTTP error. Redialling")
                    continue
                break
            companyNode, = neo4jHandle.create(node(id=imdbCompany.getID()))
            companyNode.add_labels("company")
            companyNode.update_properties({'name': imdbCompany['name']})
            self.companyIndex.add("id", companyNode['id'], companyNode)

        return companyNode

    def FindPersonInList(self, crewList, personNode):
        for p in crewList:
            if p.getID() == personNode.get_properties()['id']:
                return p
        return None

    def FindCompanyInNodes(self, imdbCompany):
        for comp in self.companyList:
            if(comp['name'].lower() == imdbCompany['name'].lower()):
                return comp
        return None

    # Reset functions
    def ResetDb(self):
        print("Clearing nodes")
        query = neo4j.CypherQuery(neo4jHandle, "start n = node(*) delete n")
        query.execute()
        self.ResetCache(["movie", "company", "person"])

    def ResetRelationships(self):
        print("Clearing relationships")
        query = neo4j.CypherQuery(
            neo4jHandle, "start r = relationship(*) delete r")
        query.execute()

    def ResetCompanies(self):
        print("Clearing company nodes")
        query = neo4j.CypherQuery(
            neo4jHandle, "MATCH (c:company) DELETE c")
        query.execute()
        self.ResetCache(["company"])

    def ResetMovies(self):
        print("Clearing movie nodes")
        query = neo4j.CypherQuery(
            neo4jHandle, "MATCH (m:movie) DELETE m")
        query.execute()
        self.ResetCache(["movie"])

    def ResetPeople(self):
        print("Clearing people nodes")
        query = neo4j.CypherQuery(
            neo4jHandle, "MATCH (p:person) DELETE p")
        query.execute()
        self.ResetCache(["person"])

    def ResetCache(self, dirList):
        for cacheDir in dirList:
            print "Clearing %s cache" % cacheDir
            os.chdir(imdbCacheDir + "/" + cacheDir)
            dirlist = [f for f in os.listdir(".") if f.endswith(".pkl")]
            for f in dirlist:
                os.remove(f)

    #
    # Mappings
    #
    def BuildCompanyMap(self, mapFile):
        mapList = {}
        query = neo4j.CypherQuery(
            neo4jHandle, "\n".join(["MATCH (p:person)-[r:WORKED_FOR]-(c:company)",
                                    "WHERE r.matchRatio > 90",
                                    "RETURN DISTINCT r.company AS search,",
                                    "COUNT(r.company) AS searchcount,",
                                    "c.name AS company,", "c.id AS id,", "r.matchRatio AS match",
                                    "ORDER BY match"]))
        result = query.execute()
        for record in result:
            mapList[record.values[0]] = {
                "id": record.values[3], "company": record.values[2]}

        mapCombined = {"maptype":"company","locations":{},"maps":mapList}
        jsonOut = open(mapFile, 'wb')
        json.dump(mapCombined, jsonOut)
        jsonOut.close()

        print str(len(result)) + " results written to map file " + mapFile

    #
    # Database updateers
    # - Anything that modifies the database AFTER initial creation
    #
    def SetTrueRoles(self):
        if scraper.roleMap:
            # Build reverse map first
            print "== Remapping true roles with rolemap file"
            # reverseMap = {}
            # for role in roleFile:
            #     if roleFile[role]['name'] in reverseMap:
            #         reverseMap[roleFile[role]['name']]['searches'].append(roleFile[role])
            #     else:
            #         reverseMap[roleFile[role]['name']] = {'id':roleFile[role]['id'], 'searches':[], 'total': 0}

            # DB query to get role relationships
            query = neo4j.CypherQuery(
                neo4jHandle, "MATCH (p:person)-[r:WORKED_FOR]-(c:company) RETURN r as roleRel")
            result = query.execute()

            for key in result:
                roleRel = key.values[0]
                trueRole = ""
                if roleRel['role'] in self.roleMap['maps']:
                    trueRole = self.roleMap['maps'][roleRel['role']]['name']
                Log.String(
                    "Mapping " + str(roleRel['role']) + " to " + str(trueRole))
                roleRel.update_properties({'trueRole': trueRole})
        else:
            print "No rolemap set!"

    def SetLocations(self):
        if scraper.companyMap:
            print "== Setting locations from companymap file"
            query = neo4j.CypherQuery(
                neo4jHandle, "MATCH (c:company) RETURN c")
            result = query.execute()

            reverseMap = {}
            companyMap = scraper.companyMap['maps']
            for company in companyMap:
                if companyMap[company]['name'] in reverseMap:
                    reverseMap[companyMap[company]['name']]['searches'].append(companyMap[company])
                else:
                    reverseMap[companyMap[company]['name']] = {'id':companyMap[company]['id'], 'searches':[], 'total': 0}
                    if 'location' in  companyMap[company]:
                        reverseMap[companyMap[company]['name']]['location'] = companyMap[company]['location']
                    else:
                        reverseMap[companyMap[company]['name']]['location'] = ""

            for key in result:
                companyProps = key.values[0].get_properties()

                if companyProps['isMapped']:
                    if companyProps['name'] in reverseMap:
                        if 'location' in reverseMap[companyProps['name']]:
                            if reverseMap[companyProps['name']]['location']:
                                latLongObj = scraper.companyMap['locations'][reverseMap[companyProps['name']]['location']]
                                print "Setting location for '" + companyProps['name'] + "': " + latLongObj['lat'] + ", " + latLongObj['long']
                                key.values[0].update_properties({'location': str(latLongObj['lat'] + " " + latLongObj['long'])})


    def SetJumpRoles(self):
        print "== Building jump paths"
        currentPerson = None
        lastCompany = ""
        pathNodeList = None
        startNode = None
        tallyStr = ""
        tallyCount = 0
        jumpCount = 0
        sameCompanyCount = 0
        query = neo4j.CypherQuery(neo4jHandle, "\n".join(
            ['MATCH (p:person)-[r:WORKED_FOR]-(c:company)',
             'RETURN p,r,c',
             'ORDER BY p.id, r.release']))
        result = query.execute()
        for key in result:

            # Get current person
            currentPersonId = "start"
            if currentPerson:
                currentPersonId = currentPerson['id']

            if key.values[0]['id'] != currentPersonId:
                # Build path for last person

                if(currentPerson):
                    # Build path
                    if(len(pathNodeList) > 0):
                        jointPath = None
                        for path in pathNodeList:
                            if not jointPath:
                                jointPath = path
                            else:
                                jointPath = neo4j.Path.join( jointPath, "JUMP", path )
                        
                        jointPath.create(neo4jHandle)
                    
                    Log.String("--- Total jumps: " + str(jumpCount))
                
                jumpCount = 0
                sameCompanyCount = 0
                tallyCount = 0
                tallyStr = ""
                lastCompany = None
                Log.String(
                    "=== New person: '" + str(key.values[0]['name']) + "'")
                currentPerson = key.values[0]

            # Get current company for person
            companyId = "start"
            if lastCompany:
                companyId = lastCompany['id']

            if key.values[2]['id'] != companyId:
                # New jump
                Log.String("Jumping ship to '" + str(
                    key.values[1]['company']) + "'")

                jumpNode = neo4jHandle.get_or_create_indexed_node('jump', 'combinedJumpId', str(currentPersonId) + "-" + str(key.values[2]['id']), {'personId': currentPersonId})
                jumpNode.add_labels("jump")
                if not lastCompany:
                    print "No last company. Setting to " + str(key.values[2]['name'])
                    jumpPath = neo4j.Path(key.values[0], "JUMP", jumpNode, "JUMP", key.values[2])
                    pathNodeList = []
                    pathNodeList.append(jumpPath)
                else:
                    jumpPath = neo4j.Path(jumpNode, "JUMP", key.values[2])
                    pathNodeList.append(jumpPath)

                tallyStr = ""
                tallyCount = 0
                lastCompany = key.values[2]
                jumpCount += 1
            else:
                # Tally up consecutive roles at the company
                sameCompanyCount += 1
                tallyStr += "-"
                tallyCount += 1
                Log.String("Stayed at '" + str(
                    key.values[1]['company']) + "' for " + tallyStr + " films (" + str(tallyCount) + ")")

        # Create the jump
        #if(lastJumpPath):
            #neo4jHandle.create(lastJumpPath)
#
# Class for storing a role and associated company
#


class VFXRole:

    def __init__(self):
        self.role = ""
        self.company = ""
        self.matchedTag = ""


# Script start
# -----------------------------------------------------

print "\n"
print "*----------------------------------*"
print "***** DWW Data Parser for IMDB *****"
print "*----------------------------------*"


# Args
parser = OptionParser()
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False)
parser.add_option("--reset-movies", action="store_true",
                  dest="resetMovies", help="Reset all movie nodes.", default=False)
parser.add_option("--reset-people", action="store_true",
                  dest="resetPeople", help="Reset all people nodes.", default=False)
parser.add_option("--reset-companies", action="store_true",
                  dest="resetCompanies", help="Reset all company nodes.", default=False)
parser.add_option("--reset-all", action="store_true",
                  dest="resetAll", help="Reset DB and cache.", default=False)
parser.add_option("-c", "--company", action="store_true",
                  dest="startCompany", help="IMDB id of root company.", default=False)
parser.add_option("-s", "--search", action="store_true",
                  dest="startSearch", help="Search term for root company", default=False)
parser.add_option("--buildCompanyMap", action="store", type="string",
                  dest="buildCompanyMapFile", help="Builds initial company map file. (matchRatio > 90)")
parser.add_option("--companymap", action="store", type="string",
                  dest="useCompanyMap", help="Map file for remapping companies."),
parser.add_option("--rolemap", action="store", type="string",
                  dest="useRoleMap", help="Map file for remapping roles."),
parser.add_option("--buildmappedroles", action="store_true",
                  dest="buildMappedRoles", help="Sets true roles from map files."),
parser.add_option("--buildjumpnodes", action="store_true",
                  dest="buildJumpNodes", help="Builds jump nodes for company jumps."),
parser.add_option("--buildlocations", action="store_true",
                  dest="buildLocations", help="Sets locations from company map."),
parser.add_option("--run", action='store_true',
                  help="Run the IMDB scraper", dest="runScraper", default=False)
(options, args) = parser.parse_args()

# Create DB handle
neo4jHandle = neo4j.GraphDatabaseService(
    "http://localhost:7474/db/data/")

# Logging
Log = Logger(options.verbose)

# IMdb scraper class
scraper = ImdbScraper()
scraper.InitIMDB()

# Recurse limits
filmographyDepth = -1

# Cache locations
imdbCacheDir = os.path.abspath("imdbCache")

# Root company ID and search terms
companyID = 5031
companySearchTag = 'weta'

if options.startCompany or options.startSearch:
    if options.startCompany and options.startSearch:
        companyID = options.startCompany
        companySearchTag = options.startSearch
    else:
        print "Both the root company ID and company search term need to be set!"
        sys.exit(1)

# Resets
if options.resetAll or options.resetCompanies or options.resetMovies or options.resetPeople:
    scraper.ResetRelationships()
    if options.resetAll:
        scraper.ResetDb()
    if options.resetCompanies:
        scraper.ResetCompanies()
    if options.resetMovies:
        scraper.ResetMovies()
    if options.resetPeople:
        scraper.ResetPeople()

# Mappings
if options.buildCompanyMapFile:
    scraper.BuildCompanyMap(options.companyMapFile)
    sys.exit(0)
if options.useCompanyMap:
    try:
        with open(options.useCompanyMap, 'rb'):
            scraper.companyMap = json.load(open(options.useCompanyMap, 'rb'))
            if scraper.companyMap['maptype'] != "company":
                print "Wrong map supplied. Expected 'company', got " + scraper.roleMap['maptype']
                sys.exit(1)
    except IOError:
        print "Couldn't find company map file"
        sys.exit(1)

if options.useRoleMap:
    try:
        with open(options.useRoleMap, 'rb'):
            scraper.roleMap = json.load(open(options.useRoleMap, 'rb'))
            if scraper.roleMap['maptype'] != "role":
                print "Wrong map supplied. Expected 'role', got " + scraper.roleMap['maptype']
                sys.exit(1)
    except IOError:
        print "Couldn't find role map file"
        sys.exit(1)

if options.buildMappedRoles:
    scraper.SetTrueRoles()
    
if options.buildLocations:
    scraper.SetLocations()

if options.buildJumpNodes:
    scraper.SetJumpRoles()

if options.runScraper:
    # Get list of people to search from root company
    scraper.SetRootCompany(companyID, companySearchTag)
    personList = scraper.GetPeopleInFilmography(filmographyDepth)

    # Make connections
    scraper.ConnectPeopleToCompanies(personList)
    if options.useRoleMap:
        scraper.SetTrueRoles()

print('===== Finished =====')
