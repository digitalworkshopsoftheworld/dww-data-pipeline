/*
 * DB setup
 */
var neo4j = require('neo4j');
var fs = require('fs');
var locUtils = require('./locUtils.js');
var companyMapFile = __dirname + '/../../utils/compMerged.json';

var db = new neo4j.GraphDatabase(process.env.NEO4J_URL || 'http://localhost:7474');

/*
 * Data dumpers
 */
exports.getAllPeopleAsCSV = function(callbackComplete) {
    var outCsv = ""
    var csvCols = ["personId", "personName", "personRole", "imdbMovieId", "searchedCompany", "searchedMatchRatio",
        "movieReleaseYear", "matchedCompanyId", "matchedCompanyName"
    ].join(",");
    var query = [
        'MATCH (p:person)-[r:WORKED_FOR]-(c:company)',
        'RETURN p,r,c',
        'ORDER BY p.id, r.release'
    ].join('\n');

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;

        for (var i = 0; i < results.length; i++) {
            var line = results[i];
            var csvLine = [
                line.p._data.data.id,
                line.p._data.data.name,
                line.r._data.data.role.replace(',', ''),
                line.r._data.data.movieID,
                line.r._data.data.company.replace(',', ''),
                line.r._data.data.matchRatio,
                line.r._data.data.release,
                line.c._data.data.id,
                line.c._data.data.name
            ].join(",") + "\n";

            outCsv += csvLine;
        }
        callbackComplete(csvCols + "\n" + outCsv);
    });
};

exports.getAllPeopleAsJson = function(callbackComplete, jumpsOnly, filterArgs) {

    //Load company map for region lookups
    fs.readFile(companyMapFile, 'utf8', function(err, data) {
        if (err) {
            console.log('Error: ' + err);
            return;
        }

        companyMap = JSON.parse(data);
    });

    var key = GetRelKeyFromFilter(filterArgs['filter']);

    //DB query
    var query = [
        'MATCH (p:person)-[r:WORKED_FOR]-(c:company)',
        'WHERE c.isMapped = true AND NOT c.geoLoc = "" AND NOT c.location = ""',
        'RETURN p,r,c',
        'ORDER BY p.id, str(r.release)'
    ].join('\n');

    var outJson = {};
    var peopleList = [];

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;
        var lastpersonId = ""
        var lastCompany = null
        var lastPersonObject = {};
        var companyLocations = {};

        for (var i = 0; i < results.length; i++) {
            var line = results[i];
            var currentPersonObject;

            if (lastPersonObject.id == line.p._data.data.id) {
                currentPersonObject = lastPersonObject;
            } else {
                if (currentPersonObject)
                    peopleList.push(currentPersonObject);

                lastCompany = null
                currentPersonObject = {
                    id: line.p._data.data.id,
                    name: line.p._data.data.name,
                    rels: []
                };
            }

            currentCompany = line.c._data.data.name;

            skipRel = false;
            if (jumpsOnly) {
                if (currentCompany == lastCompany) {
                    skipRel = true;
                }
            }

            lastCompany = currentCompany;

            if (!skipRel) {
                if (jumpsOnly) {
                    splitDate = line.r._data.data.release.split("-");
                    realDate = new Date(splitDate[0], splitDate[1], splitDate[2]).getTime();
                    currentPersonObject.rels.push({
                        imdbMovieId: line.r._data.data.movieID,
                        personMappedRole: line.r._data.data.trueRole,
                        movieReleaseYear: realDate,
                        dummy: false,
                        matchedCompanyName: line.c._data.data.name,
                        region: line.c._data.data.region,
                        location: line.c._data.data.location,
                    });

                    companyLocations[line.c._data.data.name] = line.c._data.data.location;
                } else {
                    currentPersonObject.rels.push({
                        imdbMovieId: line.r._data.data.movieID,
                        companySearch: line.r._data.data.company,
                        companyMatchRatio: line.r._data.data.matchRatio,
                        personRole: line.r._data.data.role,
                        personMappedRole: line.r._data.data.trueRole,
                        movieReleaseYear: line.r._data.data.release,
                        matchedCompanyId: line.c._data.data.id,
                        matchedCompanyName: line.c._data.data.name
                    });
                }
            }

            lastPersonObject = currentPersonObject;
        }

        //Push last person after loop finishes
        peopleList.push(lastPersonObject);
        if (jumpsOnly) {
            peopleList = FormatRels(peopleList, filterArgs);
            csvString = "person,role,date,company,location,region\n";
            //Render groupings
            if (filterArgs) {
                if (filterArgs['filter']) {
                    outJson['direction'] = filterArgs['dir'];
                    if (filterArgs['grouping'] != 'person') {
                        var jumpList = null;
                        for (var person in peopleList) {
                            person = peopleList[person];
                            if (person) {
                                for (var r in person.rels) {
                                    rel = person.rels[r];
                                    //console.log(rel.location, companyMap['regions'][rel.location]);
                                    jump = {
                                        "person": person.name,
                                        "role": rel.personMappedRole,
                                        "date": rel.movieReleaseYear,
                                        "location": rel.location.toLowerCase(),
                                        "region": companyMap['regions'][rel.location.toLowerCase()]['globalRegion'],
                                        "company": rel.matchedCompanyName
                                    };
                                    // if (filterArgs['filter'] == 'company') {
                                    //     jump['company'] = rel.matchedCompanyName;
                                    // } else if (filterArgs['filter'] == 'region') {
                                    //     jump['region'] = rel.region;
                                    // }

                                    if (filterArgs['grouping'] == 'none') {
                                        if (!jumpList) jumpList = [];
                                        jumpList.push(jump);

                                    } else if (filterArgs['grouping'] == 'keys') {
                                        var key = GetRelKeyFromFilter(filterArgs['filter']);

                                        if (!jumpList) jumpList = {};
                                        if (!jumpList[rel[key]]) {
                                            jumpList[rel[key]] = {
                                                people: [],
                                                total: 0
                                            };
                                        }

                                        jumpList[rel[key]].people.push(jump);
                                        jumpList[rel[key]].total += 1;
                                    }

                                    csvString += jump.person + "," +
                                        jump.role + "," +
                                        jump.date + "," +
                                        jump.company + "," +
                                        jump.location + "," +
                                        jump.region + "\n";
                                }
                            }
                        }

                        outJson['jumps'] = jumpList;

                        if (filterArgs['format'] == "csv") {
                            callbackComplete(csvString);
                        } else {
                            callbackComplete(outJson);
                        }
                        return;
                    }

                }
            }
        }

        if (!peopleList) {
            callbackComplete("Filter failed. Check args. (Valid: 'companies', 'regions')");
        }
        outJson['jumps'] = peopleList;
        outJson['locations'] = companyLocations;
        outJson['regions'] = companyMap['regions'];
        outJson['globalRegions'] = companyMap['globalRegions'];
        callbackComplete(outJson);
    });
};

var DaysToMs = function(days) {
    return days * 24 * 60 * 60 * 1000;
}

var GetRelKeyFromFilter = function(filterArg) {
    var key = "";
    if (filterArg == "company") {
        key = "matchedCompanyName";
    } else if (filterArg == "location") {
        key = "location";
    } else if (filterArg == "region") {
        key = "region";
    }

    return key;
}

var FormatRels = function(peopleList, args) {

    //Add dummy relationships to pad depature/arrival animations
    for (var p in peopleList) {
        var person = peopleList[p];
        var tempRels = [];

        if (!args['filter']) {
            tempRels.push(person.rels[0]);
        }

        for (var i = 1; i < person.rels.length; i++) {
            if (args['filter']) {
                //Need direction and a target to return top companies/regions
                if (!args['dir'] || !args['target']) {
                    return;
                }

                var key = GetRelKeyFromFilter(args['filter']);

                if (args['dir'] == "in" || !args['dir']) {
                    if (p < 5) console.log(person.name, "Checking", person.rels[i][key].toLowerCase());
                    //Destination matches target, add jump origin to list
                    if (person.rels[i][key].toLowerCase() == args['target'].toLowerCase()) {
                        tempRels.push(person.rels[i - 1]);
                        if (p < 5) console.log("Incoming:", person.rels[i - 1][key]);
                        if (person.rels[i - 1][key].toLowerCase() == args['target'].toLowerCase()) console.log("!!!!!!!! Incoming is same as target!");
                    }

                    if (person['name'].toLowerCase() == "Matt Bouchard".toLowerCase()) {
                        //console.log("!!!!");
                    }
                } else if (args['dir'] == "out" || !args['dir']) {
                    if (p < 5) console.log("Checking", person.rels[i - 1][key].toLowerCase());
                    //Origin matches target, add jump destination to list
                    if (person.rels[i - 1][key].toLowerCase() == args['target'].toLowerCase()) {
                        tempRels.push(person.rels[i]);
                        if (p < 5) console.log("Outgoing:", person.rels[i][key]);
                        if (person.rels[i][key].toLowerCase() == args['target'].toLowerCase()) console.log("!!!!!!!! Outgoing is same as target!");
                    }
                }
            } else {
                //No filter means we need the dummy relationships present for the visualizer
                dummyRel = {
                    imdbMovieId: person.rels[i - 1].imdbMovieId,
                    personMappedRole: person.rels[i - 1].personMappedRole,
                    movieReleaseYear: person.rels[i].movieReleaseYear - DaysToMs(locUtils.GetTripLengthDays(person.rels[i - 1].location, person.rels[i].location)),
                    dummy: true,
                    matchedCompanyName: person.rels[i - 1].matchedCompanyName,
                    region: person.rels[i - 1].region,
                };
                tempRels.push(dummyRel);
                tempRels.push(person.rels[i]);
            }
        }

        //Remove person if they have no jumps after filtering
        if (tempRels.length < 1) {
            //peopleList.splice(p, 1);
            peopleList[p] = null;
        } else {
            person.rels = tempRels;
        }
    }

    var filteredList = [];
    for (var p in peopleList) {
        var person = peopleList[p];
        if (person) {
            filteredList.push(person);
        }
    }
    peopleList = filteredList;

    return peopleList;
}


/*
 * Data listers
 */
exports.getCompanySearchList = function(callbackComplete) {
    var query = [
        "MATCH (p:person)-[r:WORKED_FOR]-(c:company)",
        "RETURN DISTINCT r.company AS search, COUNT(r.company) AS count",
        "ORDER BY count DESC, r.company"
    ].join("\n");
    var outJson = [];

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;

        var outJson = [];
        for (var i = 0; i < results.length; i++) {
            outJson.push({
                'search': results[i]['search'],
                'count': results[i]['count']
            });
        }

        callbackComplete(outJson);
    });
}


exports.getCompanyList = function(callbackComplete) {
    var query = [
        "MATCH (c:company)",
        "RETURN c.name as name, c.id as id"
    ].join("\n");
    var outJson = [];

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;

        var outJson = [];
        for (var i = 0; i < results.length; i++) {
            outJson.push({
                'company': results[i]['name'],
                'id': results[i]['id']
            });
        }

        callbackComplete(outJson);
    });
}


exports.getRoleList = function(callbackComplete) {
    var query = [
        "MATCH (p:person)-[r:WORKED_FOR]-(c:company)",
        "RETURN DISTINCT r.role AS search, COUNT(r.role) AS searchcount",
        "ORDER BY searchcount DESC, r.role"
    ].join("\n");
    var outJson = [];

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;

        console.log(results);

        var outJson = [];
        for (var i = 0; i < results.length; i++) {
            outJson.push({
                'orderid': i,
                'search': results[i]['search'],
                'searchcount': results[i]['searchcount']
            });
        }
        callbackComplete(outJson);
    });
}


exports.getCompanySearchMappings = function(callbackComplete) {
    var query = [
        "MATCH (p:person)-[r:WORKED_FOR]-(c:company)",
        "RETURN DISTINCT r.company AS search,",
        "COUNT(r.company) AS searchcount,",
        "c.name AS name,",
        "c.id AS id,",
        "r.matchRatio AS match",
        "ORDER BY search"
    ].join("\n");
    var outJson = [];

    db.query(query, params = {}, function(err, results) {
        if (err) throw err;

        var outJson = [];
        for (var i = 0; i < results.length; i++) {
            outJson.push({
                'orderid': i,
                "search": results[i]['search'],
                "searchcount": results[i]['searchcount'],
                "name": results[i]['name'],
                "id": results[i]['id'],
                "match": results[i]['match'],
            });
        }

        callbackComplete(outJson);
    });
}