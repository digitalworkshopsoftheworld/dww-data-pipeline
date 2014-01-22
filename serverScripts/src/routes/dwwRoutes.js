/*
 * Modules
 */
var dww = require('../dwwApi.js'),
    url = require('url'),
    queryString = require("querystring"),
    fs = require('fs');


/*
 * Raw data routes
 */
exports.dumpCSV = function(req, res) {
    res.set('Content-Type', 'application/octet-stream');
    dww.getAllPeopleAsCSV(function(data) {
        res.send(data);
    });
};

exports.dumpJSON = function(req, res) {
    dww.getAllPeopleAsJson(function(data) {
        res.json({
            people: data
        });
    });
};

exports.companyList = function(req, res) {
    dww.getCompanyList(function(data) {
        res.json(data);
    })
};

exports.companySearchList = function(req, res) {
    dww.getCompanySearchList(function(data) {
        res.json(data);
    })
};

exports.roleList = function(req, res) {
    dww.getRoleList(function(data) {
        res.json(data);
    })
};

exports.companyMappings = function(req, res) {
    dww.getCompanySearchMappings(function(data) {
        res.json(data);
    })
}

exports.index = function(req, res) {
    res.render('index', {
        title: 'Express'
    });
};

exports.getCompanyMap = function(req, res) {
    res.render('editor', {
        title: 'DWW - Company Search Mappings'
    });
};

exports.editCompanyMap = function(req, res) {
    //console.log(req.body);
    fs.writeFile(__dirname + '../public/js/mapFile.json', JSON.stringify(req.body), function(err) {
        if (err) return console.log(err);
        console.log('Wrote mappings to > mapFile.json');
    });

    res.writeHead(200, {
        'Content-Type': 'text/html'
    });
    res.end('updated mappings');
};