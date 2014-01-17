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

reload(sys)
sys.setdefaultencoding("utf-8")

# Import the IMDbPY package.
try:
    import imdb
    from py2neo import neo4j, node, rel
    from fuzzywuzzy import fuzz

except ImportError:
    print('Missing neo4j or imdbpy or fuzzywuzzy')
    sys.exit(1)


class ImdbScraper:

    def __init__(self):
        # IMDB interface
        self.i = imdb.IMDb()

        # Company whitelists
        self.cachedCompanySearches = {}
        self.companyWhitelist = {}

        # Indexes
        self.companyIndex = neo4jHandle.get_or_create_index(
            neo4j.Node, "company")
        self.movieIndex = neo4jHandle.get_or_create_index(
            neo4j.Node, "movie")
        self.personIndex = neo4jHandle.get_or_create_index(
            neo4j.Node, "person")

    def SetRootCompany(self, companyID, companySearchTag):
        self.companyID = companyID
        self.companySearchTag = companySearchTag
        self.rootCompany = self.i.get_company(self.companyID)

        # List of companies for quick checking against existing companies
        self.companyList = [self.rootCompany]

    def GetPeopleInFilmography(self, filmographyDepth):
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
            movDB = self.GetCachedListAndNode(movie, "movie", "visual effects")
            movNode = movDB[0]
            vfxCrew = movDB[1]

            if(vfxCrew):
                movCompanyRelationship = list(
                    neo4jHandle.match(start_node=companyNode, end_node=movNode))
                if(len(movCompanyRelationship) < 1):
                    neo4jHandle.create(
                        rel(companyNode, "FILMOGRAPHY", movNode))

                for person in vfxCrew:
                    vfxRole = self.ParseCompanyFromPersonNotes(
                        person, self.companySearchTag)
                    if(len(vfxRole.matchedTag) > 0):
                        personList[person.getID()] = person
                print("--- '" + movNode.get_properties()['name'] + "'. Scanned " + str(
                    len(vfxCrew)) + " people. Total found: " + str(len(personList)))

        print("--- Total unique employees found: " + str(len(personList)))
        print '!!! Memory usage: %s (mb)' % str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000)
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
                person, "person", "visual effects")
            personNode = personDB[0]
            personFilmography = personDB[1]

            if personFilmography:
                if len(personFilmography) < 1:
                    print(
                        " === " + str(person['name']) + " has no VFX filmography.")
                    print(person)
                    print(" === Skipping...")
                    continue

                for movie in personFilmography:
                    movDB = self.GetCachedListAndNode(
                        movie, "movie", "visual effects")
                    movNode = movDB[0]
                    vfxCrew = movDB[1]

                    personInMovie = self.FindPersonInList(vfxCrew, personNode)
                    if(personInMovie):
                        vfxRole = self.ParseCompanyFromPersonNotes(
                            personInMovie)
                        existingCompany = None

                        if vfxRole.company in self.companyWhitelist:
                            existingCompany = self.companyWhitelist[
                                vfxRole.company]
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
                                print "Skipping role '" + str(vfxRole.role) + "'. No associated company"
                                continue

                        compDB = self.GetCachedListAndNode(
                            existingCompany, "company")
                        compNode = compDB[0]
                        existingCompany = compDB[1]

                        if existingCompany:
                            print("Attach '" + str(personInMovie['name']) + "' to '" + str(
                                existingCompany['name']) + "' for '" + str(vfxRole.role) + "'")
                            self.ConnectPersonToCompany(
                                personNode, compNode, vfxRole, movNode)
                        else:
                            print("No company called '" + str(vfxRole.company) + "' for " + str(
                                person['name']) + "' under role '" + str(vfxRole.role) + "'")
                    else:
                        print("Couldn't find person in movie")
            else:
                print "No person filmography object"

            personList[personID] = None
            self.personCount += 1
            print(" === " + str(self.personCount) + "/" +
                  str(self.personTotal) + " people processed")
            print('!!! Delta Memory usage: %s (mb)' %
                  str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000 - startmem))
            print('!!! Total Memory usage: %s (mb)' %
                  str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000000))

        print('===== Finished =====')

    def ConnectPersonToCompany(self, personNode, companyNode, vfxrole, movieNode):
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
                {'role': vfxrole.role, 'company': vfxrole.company, 'movieID': movieNode.get_properties()['id'], 'release': movieNode.get_properties()['release'], 'matchRatio': fuzzyCompanyMatch})
        Log.Log("Match ratio: " + str(fuzzyCompanyMatch) + ". CompRole: " + str(vfxrole.company.lower().strip())
                  + ". Node: " + str(companyNode.get_properties()['name'].lower().strip() ))

    def GetCachedListAndNode(self, imdbObj, nodeType, listKey="", forceUpdate=False):
        cachedList = None
        cachedListPickle = None
        pickleFileName = str(
            imdbCacheDir + "/" + nodeType + "/" + str(imdbObj.getID()) + ".pkl")
        cachedNode = neo4jHandle.get_indexed_node(
            nodeType, "id", imdbObj.getID())

        if not cachedNode or forceUpdate:
            self.UpdateImdbObj(imdbObj)
            if len(listKey) > 0:
                if imdbObj.has_key(listKey):
                    cachedList = imdbObj[listKey]
            else:
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

                if nodeType == "movie":
                    year = 0
                    if imdbObj.has_key('year'):
                        year = imdbObj['year']
                    nodeProperties['release'] = int(year)
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
                Log.Log("Cached " + str(nodeType) +
                          " '" + str(nodeProperties['name']) + "'")
        else:
            try:
                with open(pickleFileName, 'rb'):
                    Log.Log("Loading " + str(nodeType) + " '" + str(
                            imdbObj.getID()) + "' from cache")
                    pickleFile = open(pickleFileName, 'rb')
                    cachedList = pickle.load(pickleFile)
                    pickleFile.close()
            except IOError:
                print "-- No pickle found, recreating cache"
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

    def FindOrCreateCompanyNode(self, imdbCompany):
        companyNode = neo4jHandle.get_indexed_node(
            "company", "id", imdbCompany.getID())
        if not companyNode:
            Log.log("Couldn't find company node. Searched for '" +
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

    def ParseCompanyFromPersonNotes(self, person, companyTag=""):
        outRole = VFXRole()
        # Remove symbols
        filtered = re.sub(r'[!@#*$\(\)\\\[\]]', '', person.notes).lower()
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
        Log.Log(
                str("Filtered: '" + str(filtered) + "'. Original: '" + str(person.notes) + "'"))
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

    def ResetDb(self):
        print("Clearing nodes")
        query = neo4j.CypherQuery(neo4jHandle, "start n = node(*) delete n")
        query.execute()

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

    def ResetCache(self):
        cacheDirs = ["movie", "person", "company"]
        for cacheDir in cacheDirs:
            print "Clearing %s cache" % cacheDir
            os.chdir(imdbCacheDir + "/" + cacheDir)
            dirlist = [f for f in os.listdir(".") if f.endswith(".pkl")]
            for f in dirlist:
                os.remove(f)



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

#Args
parser = OptionParser()
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
parser.add_option("--reset-companies", action="store_true", dest="resetCompanies", help="Reset all company nodes")
parser.add_option("--reset-all", action="store_true", dest="resetAll", help="Reset DB and cache")
parser.add_option("-c", "--company", action="store_true", dest="startCompany", help="IMDB id of root company")
parser.add_option("-s", "--search", action="store_true", dest="startSearch", help="Search term for root company")
(options, args) = parser.parse_args()

# Create DB handle
neo4jHandle = neo4j.GraphDatabaseService(
    "http://localhost:7474/db/data/")

# Logging
Log = Logger(options.verbose)

# IMdb scraper class
scraper = ImdbScraper()

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

# Main parser object
scraper.SetRootCompany(companyID, companySearchTag)
print "===== DWW Data Parser for IMDB ====="
print "------------------------------------"
print("Root company is '" + str(companyID) + "', search term is '" + str(companySearchTag) + "'")

# Resets
if options.resetAll:
    scraper.ResetCache()
    scraper.ResetRelationships()
    scraper.ResetDb()
    sys.exit(0)
elif options.resetCompanies:
    scraper.ResetRelationships()
    scraper.ResetCompanies()
    sys.exit(0)

# Get list of people to search from root company
personList = scraper.GetPeopleInFilmography(filmographyDepth)

# Make connections
scraper.ConnectPeopleToCompanies(personList)