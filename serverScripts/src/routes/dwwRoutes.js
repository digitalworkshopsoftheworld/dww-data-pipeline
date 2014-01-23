/*
 * Modules
 */
var dww = require('../dwwApi.js'),
    url = require('url'),
    queryString = require("querystring"),
    fs = require('fs');

var companyMapFile = "companyMap.json";
var roleMapFile = "roleMap.json";


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

exports.companyMapper = function(req, res) {
    res.render('editor', {
        title: 'DWW - Company Search Mappings',
        mappingType: "company",
        mappingListUrl: "list/companymap",
        mappingFile: "js/" + companyMapFile
    });
};

exports.roleMapper = function(req, res) {
    res.render('editor', {
        title: 'DWW - Role Search Mappings',
        mappingType: "role",
        mappingListUrl: "list/roles",
        mappingFile: "js/" + roleMapFile
    });
};

exports.editCompanyMap = function(req, res) {
    fs.writeFile(__dirname + '/../public/js/' + companyMapFile, JSON.stringify(req.body), function(err) {
        if (err) return console.log(err);
        console.log('Wrote mappings to > ' + companyMapFile);
    });

    res.writeHead(200, {
        'Content-Type': 'text/html'
    });
    res.end('Updated mappings');
};

exports.editRoleMap = function(req, res) {
    fs.writeFile(__dirname + '/../public/js/' + roleMapFile, JSON.stringify(req.body), function(err) {
        if (err) return console.log(err);
        console.log('Wrote mappings to > ' + roleMapFile);
    });

    res.writeHead(200, {
        'Content-Type': 'text/html'
    });
    res.end('Updated mappings');
};