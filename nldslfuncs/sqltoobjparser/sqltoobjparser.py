from moz_sql_parser import parse
import json
sql = 'select cola, colb, colc from "someschema"."mytable" where id = 1'
x = json.dumps(parse(sql))

def sqltojson(sqlstring: str):
    pass