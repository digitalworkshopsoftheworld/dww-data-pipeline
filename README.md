dww-data-pipeline
=================

Scripts and data for DWW


Required software
-----------------

- Python 2.6/2.7 
- [Neo4j 2.0.0.RC1](http://www.neo4j.org/download)
- [Node.js](http://nodejs.org/)

Install prerequisite software, clone to destination, then run 'sudo setup.sh'.

Make sure neo4j is started with 'neo4j start' in your OS of choice, then run the script 'python2 GetWeta.py connections' to populate the database fully. 'python2 GetWeta.py reset' will clear the database and IMDB cache.

Run 'startServer.sh' to run the node.js server, then access the results through [http://localhost:8007/all/json](http://localhost:8007/all/json) or [http://localhost:8007/all/dwwAllPeople.csv](http://localhost:8007/all/dwwAllPeople.csv) for json or csv formatted data respectively.

Access the frontend through [http://localhost:7474/webadmin/#/data/search//](http://localhost:7474/webadmin/#/data/search//) and run this cyper script in the query editor to see the raw data.

`MATCH (p:person)<-[r:WORKED_ON]-(c:company) WHERE r.matchRatio > 80 RETURN p,r,c ORDER BY p.id, r.release'