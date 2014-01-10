#!/bin/bash

git submodule init
git submodule update

cd serverScripts/src; npm install

cd ../../fuzzywuzzy; python2 setup.py install
cd ../imdbpy; python2 setup.py install
cd ../py2neo; python2 setup.py install
cd ..

mkdir imdbCache
mkdir imdbCache/movie
mkdir imdbCache/person
mkdir imdbCache/company