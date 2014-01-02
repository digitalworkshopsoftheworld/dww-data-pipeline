dww-data-pipeline
=================

Scripts and data for DWW


Required software
-----------------

- Python 2.6/2.7 
- [Neo4j 2.0.0.RC1](http://www.neo4j.org/download)
- Py2Neo (included)
- [IMDbPY](http://imdbpy.sourceforge.net/)

Install all of the above dependencies first. I've include Py2Neo in this, so just install by running 'python setup.py' in the py2neo folder (or 'python2 setup.py' if you're running Python 2.6/2.7 as a seperate install).

Make sure neo4j is started with 'neo4j start' in your OS of choice, then run the script 'GetWeta.py' to populate the database.
Access the frontend through [localhost:7474](http://localhost:7474) and run this cyper script in the top editor to see some data!

`MATCH (m:movie)<-[:WORKED_ON]-(p:person)-[:WORKED_FOR]->(c:company {name:"Weta Digital"}) RETURN m,p;`

