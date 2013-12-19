#!/usr/bin/env python

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# Import the IMDbPY package.
try:
    import imdb
    from py2neo import neo4j, node, rel
except ImportError:
    print('Missing neo4j or imdbpy')
    sys.exit(1)

# if len(sys.argv) != 2:
#     print 'Only one argument is required:'
#     print '  %s "companyID"' % sys.argv[0]
#     sys.exit(2)

# Hardcoded Weta company id
companyID = 5031
companySearchTag = 'weta'

# IMDB interface
i = imdb.IMDb()

#Neo4j interface
graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")
graph_db.clear()

try:
    # Get a company object with the data about the company identified by
    # the given companyID.

    # company = i.get_company(companyID)
    company = i.get_company(companyID)
    print("Searching IMDB for employees of '" + str(company['name']) + "':")

    
    # Create company node
    companyList = graph_db.get_or_create_index(neo4j.Node, "node")
    companyNode = companyList.get_or_create('name', company['name'], {'name': company['name'] })
    companyNode.add_labels("company")
    
    for movie in company['special effects companies']: 
        i.update(movie)
        print("Searching movie '" + str(movie['title']) + "' for VFX crew")
        
        # Create movie node
        movList = graph_db.get_or_create_index(neo4j.Node, "movie")
        movNode = movList.get_or_create('name', movie['title'], {'name': movie['title'] })
        movNode.add_labels("movie")
        graph_db.create( rel(companyNode, "FILMOGRAPHY", movNode) )

        for person in movie['visual effects']:
            i.update(person)

            # Split the tag for the company out of the role notes for the crew member
            splitRole = person.notes.split(": ")
            role = "--"
            comp = "--"
            print(str(person['name']) + ". Notes: '" + str(person.notes) + "'")
            if(len(splitRole) > 1):
                role = str(splitRole[0])
                comp = str(splitRole[1]).lower()
                if comp.find(companySearchTag) > -1 :
                    print("==> " + str(person['name']) + " matches '" + comp + "' under role '" + role + "'")

                    # Create person node
                    peopleList = graph_db.get_or_create_index(neo4j.Node, "person")
                    personNode = peopleList.get_or_create('name', person['name'], {'name': person['name'] })
                    personNode.add_labels('person')            
                    
                    roleNode, = graph_db.create( rel(personNode, "WORKED_ON", movNode) )
                    roleNode.update_properties({'role':role})

                    graph_db.create( rel(personNode, "WORKED_FOR", companyNode) )
        print("--- Movie complete")


except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)


if not company:
    print 'It seems that there\'s no company with companyID "%s"' % companyID
    sys.exit(4)

