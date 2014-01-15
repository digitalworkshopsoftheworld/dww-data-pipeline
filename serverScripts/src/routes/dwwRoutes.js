/*
 * Modules
 */
var dww = require('../dwwApi.js');

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

exports.allBadRelationships = function(req, res) {
    dww.getAllBadRelationships(function(data) {
        res.json(data);
    })
};