#!/usr/bin/env python

import sys
import re
import resource
import pdb
import gc
import objgraph

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
        self.cachedCompanySearches = {}

        # Neo4j interface
        self.graph_db = neo4j.GraphDatabaseService(
            "http://localhost:7474/db/data/")

    def SetRootCompany(self, companyID, companySearchTag):
        self.companyID = companyID
        self.companySearchTag = companySearchTag
        self.rootCompany = self.i.get_company(self.companyID)
        print("Searching IMDB for employees of '" +
              str(self.rootCompany['name']) + "':")

        # List of companies for quick checking for existing companies
        self.companyList = [self.rootCompany]

    def GetPeopleInFilmography(self, filmographyDepth):
        personNodeDict = {}

        self.companyIndex = self.graph_db.get_or_create_index(
            neo4j.Node, "company")
        self.movieIndex = self.graph_db.get_or_create_index(
            neo4j.Node, "movie")
        self.personIndex = self.graph_db.get_or_create_index(
            neo4j.Node, "person")

        companyNode = self.FindOrCreateCompanyNode(self.rootCompany)

        # Dummy movie list of first n movies
        movieList = []

        if(filmographyDepth < 0):
            filmographyDepth = len(
                self.rootCompany['special effects companies'])

        for i in range(filmographyDepth):
            movieList.append(self.rootCompany['special effects companies'][i])

        for movie in movieList:
            while True:
                try:
                    self.i.update(movie)
                except imdb.IMDbDataAccessError:
                    print("*** HTTP error. Redialing")
                    continue
                break
            movNode = self.FindOrCreateMovieNode(movie)

            movCompanyRelationship = list(
                self.graph_db.match(start_node=companyNode, end_node=movNode))
            if(len(movCompanyRelationship) < 1):
                self.graph_db.create(rel(companyNode, "FILMOGRAPHY", movNode))

            if movie.has_key('visual effects'):
                for person in movie['visual effects']:
                    vfxRole = self.FindCompanyFromPersonNotes(
                        person, self.companySearchTag)
                    if(len(vfxRole.matchedTag) > 0):
                        personNode = self.FindOrCreatePersonNode(person)
                        personNodeDict[person] = personNode
                print("--- '" + movie['title'] + "'. Scanned " + str(len(movie['visual effects'])) + " people. Total found: " + str(len(personNodeDict)))
            else:
                print("--- No vfx employees in " + str(movie['title']))
            movie.clear()
        print("--- Total unique employees found: " + str(len(personNodeDict)) )
        print '!!! Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return personNodeDict

    def ConnectPeopleToCompanies(self, personNodeDict, filmographyDepth):
        print("---------------------------------")
        self.ResetRelationships()

        print("Searching employee filmographies")
        for person, personNode in personNodeDict.iteritems():
            startmem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

            while True:
                try:
                    self.i.update(person)
                except imdb.IMDbDataAccessError:
                    print("*** HTTP error. Redialing")
                    continue
                break

            if(filmographyDepth < 0):
                filmographyDepth = len(person['visual effects'])

            for i in range(filmographyDepth):
                if not person.has_key('visual effects'):
                    print(" === " + str(person['name']) + " has no VFX filmography.")
                    print(person)
                    print(" === Skipping...")
                    continue

                movie = person['visual effects'][i]
                while True:
                    try:
                        self.i.update(movie)
                    except imdb.IMDbDataAccessError:
                        print("*** HTTP error. Redialing")
                        continue
                    break

                vfxRole = self.FindCompanyFromPersonNotes(movie)
                existingCompany = None
                if vfxRole.company in self.cachedCompanySearches:
                    existingCompany = self.cachedCompanySearches[vfxRole.company]

                if not existingCompany:
                    if(len(vfxRole.company) > 0):
                        print("Searching for '" + str(vfxRole.company) + "'")
                        while True:
                            try:
                                companyList = self.i.search_company(vfxRole.company)
                            except imdb.IMDbDataAccessError:
                                print("*** HTTP error. Redialling")
                                continue
                            break
                        if(len(companyList) > 0):
                            # Grab first company only
                            existingCompany = companyList[0]
                            self.cachedCompanySearches[vfxRole.company] = existingCompany
                            if len(existingCompany) > 0:
                                print("Found " + str(existingCompany['name']))

                if existingCompany:
                    print("Attach '" + str(person['name']) + "' to '" + str(
                        existingCompany['name']) + "' for '" + str(vfxRole.role) + "' in '" + str(movie['title']) + "'")
                    companyNode = self.FindOrCreateCompanyNode(existingCompany)
                    self.ConnectPersonToCompany(
                        personNode, companyNode, vfxRole, movie)
                else:
                    print("No company for '" + str(person['name']) + "' under role '" + str(vfxRole.role) + "' in '" + str(movie['title']) + "'")
                
                # cleanup movie objects
                #movie.clear()
                #del movie
            
            # cleanup person
            personNodeDict[person] = None
            person.clear()
            del person
            print ('!!! Delta Memory usage: %s (kb)' % (int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) - startmem) )
            print '!!! Total Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            gc.collect()
            #objgraph.show_most_common_types()
            #pdb.set_trace()
        print('Finished')

    def ConnectPersonToCompany(self, personNode, companyNode, vfxrole, imdbMovie):
        personCompanyRelationship = list(
            self.graph_db.match(start_node=personNode, end_node=companyNode))

        # Use fuzzy matching to see if we need to flag this relationship as one to check the company
        fuzzyCompanyMatch = fuzz.ratio(companyNode.get_properties()['name'].lower().strip(), vfxrole.company.lower().strip())

        relExists = False
        # Check for preexisting relationships to company
        for personRel in personCompanyRelationship:
            if(personRel.get_properties()["movieID"] == imdbMovie.getID()):
                relExists = True

        if not relExists:
            roleNode, =  self.graph_db.create(
                rel(personNode, "WORKED_FOR", companyNode))
            roleNode.update_properties(
                {'role': vfxrole.role, 'company': vfxrole.company, 'movieID': imdbMovie.getID(), 'release': imdbMovie['year'], 'matchRatio': fuzzyCompanyMatch})
        if not silent:
            print("Match ratio: " + str(fuzzyCompanyMatch) + ". CompRole: " + str(vfxrole.company.lower().strip()) + ". Node: " + str(companyNode.get_properties()['name'].lower().strip()) )
    
    def FindOrCreateCompanyNode(self, imdbCompany):
        companyNode = self.graph_db.get_indexed_node(
            "company", "id", imdbCompany.getID())
        if not companyNode:
            if not silent:
                print("Couldn't find company node. Searched for '" +
                  str(imdbCompany['name']) + "'. Creating...")
            while True:
                try:
                    self.i.update(imdbCompany)
                except imdb.IMDbDataAccessError:
                    print("*** HTTP error. Redialling")
                    continue
                break
            companyNode, = self.graph_db.create(node(id=imdbCompany.getID()))
            companyNode.add_labels("company")
            companyNode.update_properties({'name': imdbCompany['name']})
            self.companyIndex.add("id", companyNode['id'], companyNode)

        return companyNode

    def FindOrCreateMovieNode(self, imdbMovie):
        movNode = self.graph_db.get_indexed_node(
            "movie", "id", imdbMovie.getID())
        if not movNode:
            if not silent:
                print("Couldn't find movie node. Searched for " + str(imdbMovie.getID() + ". Creating..."))
            movNode, = self.graph_db.create(node(id=int(imdbMovie.getID())))
            movNode.add_labels("movie")

            year = ""
            if imdbMovie.has_key('year'):
                year = imdbMovie['year']

            movNode.update_properties(
                {'title': imdbMovie['title'], 'release': year})
            self.movieIndex.add("id", movNode['id'], movNode)

        return movNode

    def FindOrCreatePersonNode(self, imdbPerson):
        personNode = self.graph_db.get_indexed_node(
            "person", "id", imdbPerson.getID())

        if not personNode:
            if not silent:
                print("Couldn't find person node. Searched for " + str(imdbPerson.getID() + ". Creating..."))
            personNode, = self.graph_db.create(node(id=imdbPerson.getID()))
            personNode.add_labels("person")
            personNode.update_properties({'name': imdbPerson['name']})
            self.personIndex.add("id", personNode['id'], personNode)

        return personNode

    def FindCompanyFromPersonNotes(self, person, companyTag=""):
        outRole = VFXRole()
        filtered = re.sub('[!@#$\(\)\[\]]', '', person.notes).rstrip()
        #filtered = re.sub('r[^\w]', '', person.notes).rstrip()
        
        splitRole = []

        try:
            splitRole = filtered.split(": ")
        except:
            print("Something went wrong splitting roles")

        role = ""
        comp = ""
        if not silent:
            print(str("Finding company from notes: '" + str(filtered) + "'"))
        if(len(splitRole) > 1):
            role = str(splitRole[0])
            comp = str(splitRole[1]).lower()
            splitComp = comp.split(' - ')
            if(len(companyTag) > 0):
                if comp.find(self.companySearchTag) > -1:
                    outRole.matchedTag = companyTag
            outRole.role = role
            outRole.company = splitComp[0]
        else:
            outRole.role = role

        return outRole

    def FindCompanyInNodes(self, imdbCompany):
        for comp in self.companyList:
            if(comp['name'].lower() == imdbCompany['name'].lower()):
                return comp
        return None

    def ResetDb(self):
        print("Clearing neo4j db")
        scraper.graph_db.clear()

    def ResetRelationships(self):
        print("Clearing relationships")
        neo4j.CypherQuery(self.graph_db, 'start r=relationship(*) delete r').execute()

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
scraper = ImdbScraper()


# Start arguments
filmographyDepth = -1

# Hardcoded Weta company id
companyID = 5031
companySearchTag = 'weta'

silent = True

if len(sys.argv) <= 1:
    print("Usage: python2 GetWeta.py (employees/connections/reset/reset_relationships)")

if len(sys.argv) > 1:
    print("Starting...")
    scraper.SetRootCompany(companyID, companySearchTag)

    if(sys.argv[1] == "reset"):
        scraper.ResetDb()
    elif(sys.argv[1] == "reset_relationships"):
        scraper.ResetRelationships()
    elif(sys.argv[1] == "employees"):
        print("Searching for employees in filmography...")
        scraper.GetPeopleInFilmography(filmographyDepth)
    elif(sys.argv[1] == "connections"):
        print("Searching for employees in filmography...")
        personList = scraper.GetPeopleInFilmography(filmographyDepth)
        scraper.ConnectPeopleToCompanies(personList, filmographyDepth)
    
