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

app.set('views', __dirname + '/../views');
app.set('view engine', 'jade');
app.use(express.logger('dev'));
app.use(express.static(__dirname + '/../public'));
app.use(app.router);

var db = new neo4j.GraphDatabase(process.env.NEO4J_URL || 'http://localhost:7474');

/*
 * App requests
 */

// Main page
app.get('/', function(req, res) {
    res.render('index', {
        locals: {
            title: 'Hello'
        }
    });
});


app.get('/all', function(req, res) {
  var query = [
        'MATCH (p:person)-[r:WORKED_FOR]-(c:company)',
        'WHERE r.matchRatio > 80',
        'RETURN p,r,c'
    ].join('\n');

    outJson = []

    db.query(query, params = {}, function(err,  results){
      if (err) throw err;

      for(var i = 0; i < results.length; i++){
        line = results[i];
        jsonLine = {
          p:{
            id:line.p._data.data.id, 
            name:line.p._data.data.name
          }, 
          r:{
            id:line.r._data.data.id, 
            company:line.r._data.data.company, 
            matchRatio:line.r._data.data.matchRatio, 
            role:line.r._data.data.role, 
            release:line.r._data.data.release
          }, 
          c:{
            id:line.c._data.data.id, 
            name:line.c._data.data.name
          }
        };
        outJson.push(jsonLine);
      }

      res.json({data:outJson});
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