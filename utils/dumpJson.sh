#!/bin/sh

curl -o dbDump.json -H accept:application/json -H content-type:application/json -d '{"query" : "MATCH (p:person)-[r:WORKED_FOR]-(c:company) WHERE r.matchRatio > 80 RETURN p,r,c" }' http://localhost:7474/db/data/cypher