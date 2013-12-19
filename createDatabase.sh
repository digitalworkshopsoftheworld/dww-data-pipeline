#!/bin/bash

python2 ../../alberanid-imdbpy-4f4451e0d91d/bin/imdbpy2sql.py -o sqlalchemy --fix-old-style-titles -d imdbLocalDb -u mysql://dww:toothpick@localhost/imdb -c CSVconvert --csv-only-write
python2 ../../alberanid-imdbpy-4f4451e0d91d/bin/imdbpy2sql.py -o sqlalchemy --fix-old-style-titles -d imdbLocalDb -u mysql://dww:toothpick@localhost/imdb -c CSVconvert --csv-only-load
