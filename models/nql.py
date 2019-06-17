from models.selectstate import SelectState
from models.wherestate import WhereState
from models.orderstate import OrderState
from nldslfuncs import wordsimilarity
# from nldslfuncs.reader import inltoobj
from moz_sql_parser import parse
import numpy as np

VERBOSE = True
class NQL:

    def __init__(self):
        self.selstate = SelectState(VERBOSE)
        self.wherestate = WhereState()
        self.orderstate = OrderState()
        self.entity = "flight"  # maybe not needed
        self.title = "Suggestion" # for the interactive GUI
        self.wikisqltableschema = {}


    def __str__(self):
        return self.sql()+"\n\n"+"-"*10+"\n\n"+self.inl()

    def sql(self):
        resultstr = str(self.selstate)
        if len(self.wherestate.wherestates) > 0:
            resultstr += " " + str(self.wherestate)
        if self.orderstate.ordercol != "":
            resultstr += " "+str(self.orderstate)
        return resultstr

    def inl(self,question=False):
        # different cases, because of  the order state:
        # if we have a fixed amount of the entries
        # or the one column is the one to be ordered by, then it makes sense to use
        # sentences like "show the cheapest/highest..., WHERE..."
        # instead of "show the COLX, COLY,...WHERE...and (sort it by) /for which COLZ is the highest...

        if self.orderstate.limit > 1 or ( # a special case for sentences like "show the 2 highest prices, where... experimental, not implemented for release yet
                len(self.selstate.selcols) == 1 and self.selstate.selcols[0] == self.orderstate.ordercol):
            return str(self.orderstate.inl(inline=True,question=question)) +" "+ self.wherestate.inl()
        else:
            result : str = self.selstate.inl(question=question)+" "+self.wherestate.inl() + " "+self.orderstate.inl(question=question)
            return result.strip()

    @classmethod
    def fromwikisql(cls, sqldict :dict, table : dict):
        testresult = {'sel': 3, 'conds': [[5, 0, 'Butler CC (KS)']], 'agg': 0}
        testtable = {"header": ["Player", "No.", "Nationality", "Position", "Years in Toronto", "School/Club Team"], "page_title": "Toronto Raptors all-time roster", "types": ["text", "text", "text", "text", "text", "text"], "id": "1-10015132-11", "section_title": "L", "caption": "L", "rows": [["Antonio Lang", "21", "United States", "Guard-Forward", "1999-2000", "Duke"], ["Voshon Lenard", "2", "United States", "Guard", "2002-03", "Minnesota"], ["Martin Lewis", "32, 44", "United States", "Guard-Forward", "1996-97", "Butler CC (KS)"], ["Brad Lohaus", "33", "United States", "Forward-Center", "1996", "Iowa"], ["Art Long", "42", "United States", "Forward-Center", "2002-03", "Cincinnati"], ["John Long", "25", "United States", "Guard", "1996-97", "Detroit"], ["Kyle Lowry", "3", "United States", "Guard", "2012-Present", "Villanova"]], "name": "table_10015132_11"}


        agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
        cond_ops = ['=', '>', '<', 'OP']

        # the object which will be returned.
        obj = cls()
        if "caption" in table.keys():
            obj.selstate.entity = table["caption"]
        elif "name" in table.keys():
            obj.selstate.entity = table["name"]
        else:
            obj.selstate.entity = table["unknown_tablename"]

        # the 'schema', or the columns
        obj.wikisqltableschema = table
        columns = table["header"]

        # aggregation:
        if sqldict["agg"] != 0: # no normal select
            obj.selstate.agg= agg_ops[sqldict["agg"]]

        #add the columns selected
        colindex = sqldict["sel"]
        if type(colindex)==int or type(colindex)==np.int64:
            obj.selstate.selcols.append(columns[colindex])
        elif type(colindex)==list:
            obj.selstate.selcols += columns[colindex]

        # add cond
        for cond in sqldict["conds"]:
            ccol = columns[cond[0]]
            rel = cond_ops[cond[1]]
            value = cond[2]
            obj.wherestate.wherestates.append([ccol,rel,value])
        return obj

    def wikisqldict(self):

        agg_ops = ['', 'MAX', 'MIN', 'COUNT', 'SUM', 'AVG']
        cond_ops = ['=', '>', '<', 'OP']

        result = {}
        # if there are no wikisql columns to compare, then the sql object has been created
        # without an wikisql training input
        if len(self.wikisqltableschema.keys())==0:
            print("ERROR: NO WIKISQL Table schema found!")
            return {}

        # -----SELECT STATEMENT COLUMNS
        selcols = []
        for selcol in self.selstate.selcols: # for each column for select statement
            if wordsimilarity.findsimilarindex(selcol,self.wikisqltableschema["header"]) !=-1: # check if is in the list of table schema columns
                pos = self.wikisqltableschema["header"].index(selcol) # add the position to the sel cols
                selcols.append(pos)
        if len(selcols) == 1: #most of the cases there is just one column being selected
            result["sel"] = selcols[0]
        elif len(selcols) > 1:
            result["sel"] = selcols
        else:
            print("NO MATCHING COLUMN FOUND FOR SELECT STATEMENT IN THE WIKISQL SCHEMA COLUMNS")
            result["sel"] = None

        # ----AGG
        if self.selstate.agg == "":
            result["agg"] = 0
        else:
            result["agg"] = agg_ops.index(self.selstate.agg)

        #---COND
        conditions = []
        for cond in self.wherestate.wherestates:
            ref = cond[0] # e.g. price
            op = cond[1] # e.g. <
            value = cond[2] # e.g. 500
            if wordsimilarity.findsimilarindex(ref,self.wikisqltableschema["header"]) !=-1 : #column must be in the list of schema columns
                colindex = self.wikisqltableschema["header"].index(ref)
            else: # if not, nothing can be done, maybe
                continue
            opindex = cond_ops.index(op)
            conditions.append([colindex,opindex,value])
        result["conds"] = conditions

        return result

    @staticmethod
    def frominl(inlstring : str,verbose=VERBOSE):
        from models import inltoobj
        sqlobj = inltoobj.inltosqlobj(inlstring,verbose=verbose)
        return sqlobj

    @classmethod
    def fromsql(cls, sqlstring: str):
        teststr =  {'select': [{'value': 'cola'}, {'value': 'colb'}, {'value': 'colc'}], 'from': 'someschema.mytable', 'where': {'and': [{'eq': ['id', 1]}, {'lte': ['b', 5]}, {'gte': ['c', 4]}, {'lt': ['a', 3]}, {'gt': ['b', 4]}, {'neq': ['a', 4]}]}}
        test2 = {'select': {'value': {'max': 'apfel'}}, 'from': 'xy', 'where': {'or': [{'eq': ['asf', {'literal': 'wert'}]}, {'lt': ['safsa', 5]}]}}
        sqldict = parse(sqlstring)
        obj = cls()
        #selstate columns
        # if there is just one column to be selected, then the key 'select' doesnt have a list with one dictionary, but just the dictionary:
        if type(sqldict["select"])==str and sqldict["select"]=="*":
            obj.selstate.selcols.append(sqldict["from"])
        else:
            if type(sqldict["select"])==dict:
                sqldict["select"] = [sqldict["select"]]
            for e in sqldict["select"]:
                v = e["value"]
                if type(v) == dict: # in cases, when there is an aggregator like {'value': {'max': 'price'}}
                    agg = [*v][0] #get the first (and only key) which is also the aggregator
                    col = v[agg]
                    obj.selstate.selcols.append(col)
                    obj.selstate.agg = agg.upper()
                    # the specification just allows one column, when an aggregator is used, therefore the break
                    break
                obj.selstate.selcols.append(v)
        # table name:
        obj.entity = sqldict["from"]
        obj.selstate.entity = sqldict["from"]

        # wherestate
        opdict = {"eq": "=","lt":"<","lte":"<=","gt":">","gte":">=","neq":"!="}
        if "where" not in sqldict.keys():
            return obj
        wheredict = sqldict["where"]
        #specification just allows either just ANDs or just ORs
        andor = [*wheredict][0]
        if andor.lower() == "and":
            obj.wherestate.conj = "AND"
        elif andor.lower() == "or":
            obj.wherestate.conj = "OR"
        #if its neither and, nor 'or', then there are NO multiple rel conditions.
        else:
            relop = [*wheredict][0].lower()
            col = wheredict[relop][0]
            # the third value is a pure value, if its a number, otherwise a dictionary
            if type(wheredict[relop][1]) == dict:
                valuekey = [*wheredict[relop][1]][0]
                value = wheredict[relop][1][valuekey]
            else:
                value = wheredict[relop][1]
            op = opdict[relop]
            obj.wherestate.wherestates.append([col, op, value])
            return obj

        #the data type for one relation condition is different than from multiple:
        if type(wheredict[andor][0]!=dict):
            pass
        for relation in wheredict[andor]:
            relop = [*relation][0].lower()
            col = relation[relop][0]
            # the third value is a pure value, if its a number, otherwise a dictionary
            if type(relation[relop][1]) == dict:
                valuekey = [*relation[relop][1]][0]
                value = relation[relop][1][valuekey]
            else:
                value = relation[relop][1]
            op = opdict[relop]
            obj.wherestate.wherestates.append([col,op,value])
        return obj

    # def orderinl(self):
    #     # if limit is 1:
    #         # things like "show the highest ..."
    #         # or "show the ... for which COL is the highest
    #
    #     # if there are more than 1 allowed
    #         # show the 10 highest
    #         # and sort them by
    #
    #     # case 1: for which COL is the highest
    #     # colname, limit=1, asc
    #     if self.orderstate.limit==1 and self.orderstate.ascending != "":
    #         output = "for which "+self.orderstate.ordercol+" is the "
    #         superlative = ""
    #         if self.orderstate.superlative != "":
    #             superlative = self.orderstate.superlative
    #         elif self.orderstate.ascending == "ASC":
    #             superlative = "lowest"
    #         else:
    #             superlative = "highest"
    #         output += superlative
    #
    #         return output
    #     elif self.orderstate.ordercol != "": # if there orderby statement exists
    #         if self.orderstate.limit ==0:
    #             return "and sort them by "+self.orderstate.ordercol
    #         else:
    #             output = "show the "+str(self.orderstate.limit)+" "
    #             if self.orderstate.superlative != "":
    #                 superlative = self.orderstate.superlative
    #             elif self.orderstate.ascending == "ASC":
    #                 superlative = "lowest"
    #             else:
    #                 superlative = "highest"
    #             output += superlative+" "+ self.orderstate.ordercol if self.orderstate.entity =="" else self.orderstate.entity
    #             return output
    #     return ""
    #
    #
    # def selectstring(self):
    #     output = "SELECT "
    #     if len(self.selstate.selcols) == 1 and (self.selstate.entity != "" and self.selstate.selcols[0] == self.selstate.entity):
    #         output += "* "
    #     else:
    #         for col in self.selstate.selcols:
    #             output += col + ", "
    #         output = output[:-2]
    #     return output + " FROM " + self.selstate.entity
    #
    # def selectinl(self):
    #     output = "show the "
    #     if self.selstate.wholerow:
    #         return "show the " + self.selstate.entity
    #     else:
    #         if len(self.selstate.selcols) == 1:
    #             output += self.selstate.selcols[0]
    #         else:
    #             for col in self.selstate.selcols[:-1]:
    #                 output += col + ", "
    #             output = output[:-2]
    #             output += " and " + self.selstate.selcols[-1]
    #         return output