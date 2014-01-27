/*
 * Modules
 */
var dww = require('../dwwApi.js'),
    url = require('url'),
    queryString = require("querystring"),
    fs = require('fs');

var companyMapFile = "companyMap";
var roleMapFile = "roleMap";


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
        title: 'DWW - Company Search maps',
        mappingType: "company",
        mappingListUrl: "list/companymap",
        mappingFile: "js/" + companyMapFile + ".json",
        blacklist: []
    });
};

exports.roleMapper = function(req, res) {
    res.render('editor', {
        title: 'DWW - Role maps',
        mappingType: "role",
        mappingListUrl: "list/roles",
        mappingFile: "js/" + roleMapFile + ".json",
        blacklist: [
            "2D",
            "3D",
            "2-d",
            "3-d",
            "Assistant",
            "Associate",
            "Supervisor",
            "Digital",
            "Head of",
            "Senior",
            "Supervising",
            "Stereoscopic",
            "Stereo",
            "Junior",
            "Lead",
            "On Set",
            "Runner",
            "Modelmaker"
        ]
    });
};

exports.editCompanyMap = function(req, res) {
    var source = __dirname + '/../public/js/' + companyMapFile + ".json";
    var dest = __dirname + '/../public/js/map_backups/' + companyMapFile + "_" + Math.round(new Date().getTime() / 1000) + ".json";
    console.log("Backing up " + source + "\nto\n" + dest);
    copyFileSync(source, dest);

    fs.writeFile(__dirname + '/../public/js/' + companyMapFile + ".json", JSON.stringify(req.body), function(err) {
        if (err) return console.log(err);
        console.log('Wrote mappings to > ' + companyMapFile + ".json");
    });

    res.writeHead(200, {
        'Content-Type': 'text/html'
    });
    res.end('Updated mappings');
};

exports.editRoleMap = function(req, res) {
    var source = __dirname + '/../public/js/' + roleMapFile + ".json";
    var dest = __dirname + '/../public/js/map_backups/' + roleMapFile + "_" + Math.round(new Date().getTime() / 1000) + ".json";
    console.log("Backing up " + source + "\nto\n" + dest);
    copyFileSync(source, dest);

    fs.writeFile(__dirname + '/../public/js/' + roleMapFile + ".json", JSON.stringify(req.body), function(err) {
        if (err) return console.log(err);
        console.log('Wrote mappings to > ' + roleMapFile + ".json");
    });

    res.writeHead(200, {
        'Content-Type': 'text/html'
    });
    res.end('Updated mappings');
};

copyFileSync = function(source, dest) {
    data = fs.readFileSync(source, "utf8");
    fs.writeFile(dest, data, function(err) {
        if (err) {
            console.log(err);
        }
    });
}