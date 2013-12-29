#!/usr/bin/env python

import sys
import re

reload(sys)
sys.setdefaultencoding("utf-8")

# Import the IMDbPY package.
try:
    import imdb
    from py2neo import neo4j, node, rel
except ImportError:
    print('Missing neo4j or imdbpy')
    sys.exit(1)


class ImdbScraper:

    def __init__(self):
        # IMDB interface
        self.i = imdb.IMDb()

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

        # for movie in company['special effects companies']:
        for movie in movieList:
            self.i.update(movie)
            movNode = self.FindOrCreateMovieNode(movie)

            movCompanyRelationship = list(
                self.graph_db.match(start_node=companyNode, end_node=movNode))
            if(len(movCompanyRelationship) < 1):
                self.graph_db.create(rel(companyNode, "FILMOGRAPHY", movNode))

            for person in movie['visual effects']:
                vfxRole = self.FindCompanyFromPersonNotes(
                    person, self.companySearchTag)
                if(len(vfxRole.company) > 0):
                    personNode = self.FindOrCreatePersonNode(person)
                    personNodeDict[person] = personNode

            print("--- Movie complete")
        print("--- Total unique employees found: " + len(personNodeDict) )

        return personNodeDict

    def ConnectPeopleToCompanies(self, personNodeDict, filmographyDepth):
        print("---------------------------------")
        print("Searching employee filmographies")
        for person, personNode in personNodeDict.iteritems():
            self.i.update(person)

            if(filmographyDepth < 0):
                filmographyDepth = len(person['visual effects'])

            for i in range(filmographyDepth):
                if(i >= len(person['visual effects'])):
                    break

                movie = person['visual effects'][i]
                self.i.update(movie)

                vfxRole = self.FindCompanyFromPersonNotes(movie)
                existingCompany = self.FindCompanyInNodes(vfxRole.company)

                if not existingCompany:
                    print("Searching for '" + str(vfxRole.company) + "'")
                    if(len(vfxRole.company) > 0):
                        companyList = self.i.search_company(vfxRole.company)
                        if(len(companyList) > 0):
                            # Grab first company only
                            existingCompany = companyList[0]
                            if len(existingCompany) > 0:
                                print("Found " + str(existingCompany['name']))

                if existingCompany:
                    print("Attach '" + str(person['name']) + "' to '" + str(
                        existingCompany['name']) + "' for '" + str(vfxRole.role) + "' in '" + str(movie['title']) + "'")
                    companyNode = self.FindOrCreateCompanyNode(existingCompany)
                    self.ConnectPersonToCompany(
                        personNode, companyNode, vfxRole.role, movie)
                else:
                    print("Could not find company.")
        print('Finished')

    def ConnectPersonToCompany(self, personNode, companyNode, role, imdbMovie):
        personCompanyRelationship = list(
            self.graph_db.match(start_node=personNode, end_node=companyNode))

        relExists = False
        # Check for preexisting relationships to company
        for personRel in personCompanyRelationship:
            if(personRel.get_properties()["movieID"] == imdbMovie.getID()):
                relExists = True

        if not relExists:
            roleNode, =  self.graph_db.create(
                rel(personNode, "WORKED_FOR", companyNode))
            roleNode.update_properties(
                {'role': role, 'movieID': imdbMovie.getID(), 'release': imdbMovie['year']})

    def FindOrCreateCompanyNode(self, imdbCompany):
        companyNode = self.graph_db.get_indexed_node(
            "company", "id", imdbCompany.getID())
        if not companyNode:
            print("Couldn't find company node. Searched for '" +
                  str(imdbCompany['name']) + "'. Creating...")
            self.i.update(imdbCompany)
            companyNode, = self.graph_db.create(node(id=imdbCompany.getID()))
            companyNode.add_labels("company")
            companyNode.update_properties({'name': imdbCompany['name']})
            self.companyIndex.add("id", companyNode['id'], companyNode)

        return companyNode

    def FindOrCreateMovieNode(self, imdbMovie):
        movNode = self.graph_db.get_indexed_node(
            "movie", "id", imdbMovie.getID())
        if not movNode:
            print(
                "Couldn't find movie node. Searched for " + str(imdbMovie.getID() + ". Creating..."))
            movNode, = self.graph_db.create(node(id=int(imdbMovie.getID())))
            movNode.add_labels("movie")
            movNode.update_properties(
                {'title': imdbMovie['title'], 'release': imdbMovie['year']})
            self.movieIndex.add("id", movNode['id'], movNode)

        return movNode

    def FindOrCreatePersonNode(self, imdbPerson):
        personNode = self.graph_db.get_indexed_node(
            "person", "id", imdbPerson.getID())

        if not personNode:
            print(
                "Couldn't find person node. Searched for " + str(imdbPerson.getID() + ". Creating..."))
            personNode, = self.graph_db.create(node(id=imdbPerson.getID()))
            personNode.add_labels("person")
            personNode.update_properties({'name': imdbPerson['name']})
            self.personIndex.add("id", personNode['id'], personNode)

        return personNode

    def FindCompanyFromPersonNotes(self, person, companyTag=""):
        outRole = VFXRole()
        filtered = re.sub('[!@#$\(\)]', '', person.notes).rstrip()
        splitRole = []

        try:
            splitRole = filtered.split(": ")
        except:
            print("Something went wrong splitting roles")

        role = "--"
        comp = "--"
        print(str("Finding company from notes: '" + str(filtered) + "'"))
        if(len(splitRole) > 1):
            role = str(splitRole[0])
            comp = str(splitRole[1]).lower()
            if(len(companyTag) > 0):
                if comp.find(self.companySearchTag) > -1:
                    outRole.matchedTag = companyTag

            outRole.role = role
            outRole.company = comp

        return outRole

    def FindCompanyInNodes(self, companyname):
        for comp in self.companyList:
            if(comp['name'].lower() == companyname.lower()):
                return comp
        return None

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


if len(sys.argv) <= 1:
    print("Usage: python2 GetWeta.py (employees/connections/reset)")
    sys.exit(0)

if len(sys.argv) > 1:
    print("Starting...")
    scraper.SetRootCompany(companyID, companySearchTag)

    if(sys.argv[1] == "reset"):
        print("Clearing neo4j db")
        scraper.graph_db.clear()
        sys.exit(0)
    elif(sys.argv[1] == "employees"):
        print("Searching for employees in filmography...")
        scraper.GetPeopleInFilmography(filmographyDepth)
    elif(sys.argv[1] == "connections"):
        print("Searching for employees in filmography...")
        personList = scraper.GetPeopleInFilmography(filmographyDepth)
        scraper.ConnectPeopleToCompanies(personList, filmographyDepth)
        sys.exit(0)
