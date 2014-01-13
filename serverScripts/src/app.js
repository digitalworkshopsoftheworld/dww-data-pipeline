/*
 * Dependencies
 */
var express  = require('express')
  , http     = require('http')
  , neo4j    = require('neo4j');


/*
 * App Setup
 */
var app = express();

var getAllQuery = [
    'MATCH (p:person)-[r:WORKED_FOR]-(c:company)',
    'RETURN p,r,c',
    'ORDER BY p.id, r.release'
].join('\n');

app.set('views', __dirname + '/../views');
app.set('view engine', 'jade');
app.use(express.logger('dev'));
app.use(express.static(__dirname + '/../public'));
app.use(app.router);

var db = new neo4j.GraphDatabase(process.env.NEO4J_URL || 'http://localhost:7474');


/*
 * App requests
 */

//Cross domain scripting allowance
 app.all('/', function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "X-Requested-With");
  next();
 });


// Main page
app.get('/', function(req, res) {
    res.render('index', {
        locals: {
            title: 'Hello'
        }
    });
});


// Route for returning csv data
app.get('/all/dwwAllPeople.csv', function(req, res) {
    db.query(getAllQuery, params = {}, function(err,  results){
      if (err) throw err;
      
      var csvCols = ["personId", "personName", "personRole", "imdbMovieId", "searchedCompany", "searchedMatchRatio",
                  "movieReleaseYear", "matchedCompanyId", "matchedCompanyName"].join(",")
      var outCsv = "" 
      for(var i = 0; i < results.length; i++){
        var line = results[i];
        var csvLine = [
          line.p._data.data.id, 
          line.p._data.data.name,
          line.r._data.data.role, 
          line.r._data.data.movieID, 
          line.r._data.data.company,  
          line.r._data.data.matchRatio, 
          line.r._data.data.release,
          line.c._data.data.id, 
          line.c._data.data.name
        ].join(",") + "\n";
        
        outCsv += csvLine;
      }

      res.set('Content-Type', 'application/octet-stream');
      res.send(csvCols + "\n" + outCsv);
    });  
});


// Route for returning json data
app.get('/all/json', function(req, res) {
    db.query(getAllQuery, params = {}, function(err,  results){
      if (err) throw err;
      var outJson = []
      var lastpersonId = ""
      var lastPersonObject = {};

      for(var i = 0; i < results.length; i++){
        var line = results[i];
        var currentPersonObject;

        if(lastPersonObject.id == line.p._data.data.id){
          currentPersonObject = lastPersonObject;
        } else {
          if(currentPersonObject)
            outJson.push(currentPersonObject);
          
          currentPersonObject = {
            id:line.p._data.data.id, 
            name:line.p._data.data.name, 
            rels:[]
          };
        }

        currentPersonObject.rels.push({
          imdbMovieId:line.r._data.data.movieID, 
          companySearch:line.r._data.data.company, 
          companyMatchRatio:line.r._data.data.matchRatio, 
          personRole:line.r._data.data.role, 
          movieReleaseYear:line.r._data.data.release,
          matchedCompanyId:line.c._data.data.id, 
          matchedCompanyName:line.c._data.data.name
        });

        lastPersonObject = currentPersonObject;
      }

      //Push last person after loop finishes
      outJson.push(lastPersonObject);

      res.json({people:outJson});
    });  
});


// 404
app.get('*', function(req, res) {
    res.writeHead(404, {'Content-Type': 'text/plain'});
    res.end("404");
});


/*
 * Start the Application
 */

app.listen(8007);