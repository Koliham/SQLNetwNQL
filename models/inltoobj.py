# this scripts converts an input string (as a list of words) and an context
# to a SQL structure

from models.nql import NQL
from models.context import Context
from collections import OrderedDict
from models.relationdict import RelationDict
import copy
#needed for plural check
from nltk.stem import WordNetLemmatizer
from nldslfuncs import preprocessor
wnl = WordNetLemmatizer()


def isplural(word):
    lemma = wnl.lemmatize(word, 'n')
    plural = True if word is not lemma else False
    return plural, lemma

def getstopwords():
    return ["and",",","the"]

def relationtranslate(self, rel):
    if rel == "<":
        return "is lower than"
    elif rel == "<=":
        return "is below"
    elif rel == ">":
        return "is higher than"
    elif rel == ">=":
        return "is above"
    elif rel == "!=":
        return "is not"
    else:
        return "is"


def _inltosql(input: list, context:Context = None,verbose=False):

    # return SQL Object
    stopwords = getstopwords()
    results = []
    print("running select extract")
    sqlstate = NQL()
    aggwords = sqlstate.selstate.aggwords
    relationhelper = RelationDict()
    orderbyfinished = False
    # show (the) [ENTITY/COL](,COLY,COLZ...and COLZ), where
    state = "" # lookfor "show...", "where..." or "order by..."
    selcols = []
    wherestatements = []
    countdone = False
    skips = 0
    for i, wort in enumerate(input):
        if skips > 0:
            skips -= 1
            continue


        if wort.lower() == "show":
            state = "show"
            continue

        if wort.lower()== "count":
            state= "count"
            continue

        if wort.lower() == "where":
            state="where"
            continue

        if wort.lower() == "for" and len(input)> i+1:
            if (input[i+1]== "which"):
                state = "orderby1"
                continue

        if state=="show":
        # now the where statements begin in the next loop
            if wort in stopwords:
                continue

            # case if aggregation occurs:
            # if wort in aggwords.keys():
            #     sqlstate.selstate.agg = aggwords[wort]
            #     continue
            #special case multiple words like for sum:
            aggmatch = False
            for aggphrase in aggwords.keys(): #"sum all", "min" etc.
                aggwoerter : list= aggphrase.split()
                try:
                    aggmatch = all([input[i+k]==aggwoerter[k] for k, co in enumerate(aggwoerter)])
                except IndexError as e:
                    pass
                if aggmatch: #if a the current word (and the nachfolger match)
                    sqlstate.selstate.agg = aggwords[aggphrase]
                    skips = len(aggwoerter) -1
                    break
            if aggmatch:
                continue

            if verbose:
                selcols.append(wort)
            else:
                plurayesno, singular = isplural(wort)
                selcols.append(singular)

        if state=="count":
            if countdone:
                continue
            if wort in stopwords:
                continue
            sqlstate.selstate.count = True
            sqlstate.selstate.agg = "COUNT"
            #for count, the name of the column is usually in plural, but the column is singular
            if verbose:
                selcols.append(wort)
            else:
                plurayesno, singular = isplural(wort)
                selcols.append(singular)

            countdone = True

        if state=="where":
            if wort == "or":
                sqlstate.wherestate.conj="OR" # one or is enough to tell that the conjugation is over OR
                continue

            if wort == "is":
                # the previous word is the column
                # the next word(s) is the relation and the argument
                col = input[i - 1]
                # check the relation:
                relation, skip = relationhelper.nltosql(input[i:i + 3])
                if (i + skip) < len(input):  # if words after "is exists"
                    value = input[i + skip]
                    wherestatements.append([col, relation, value])

        if state=="orderby1" and not orderbyfinished:
            if wort=="the":
                continue
            if wort=="which":
                continue
            colname = wort
            try:
                superlativ = input[i+3]
                sqlstate.orderstate.ordercol = colname
                sqlstate.orderstate.limit = 1
                if superlativ=="lowest":
                    sqlstate.orderstate.ascending="ASC"
                else:
                    sqlstate.orderstate.ascending="DESC"

            except:
                print("couldnt create orderby")
            orderbyfinished=True

    sqlstate.selstate.selcols = selcols
    # if the number of columns is one, than it is not clear
    sqlstate.wherestate.wherestates = wherestatements
    # results.append([0.5,sqlstate])

    sqlstate.title = sqlstate.inl()

    return sqlstate

    #if there is one




def inltoSQLstatement(input : str, context : Context = None):
    sqlobj : NQL = inltosqlobj(input, context)
    return sqlobj.sql()


def inltosqlobj(input : str, context: Context = None,verbose=False):
    input_cleaned = preprocessor.preprocessnl(input)
    #look for the word show
    wordlist = preprocessor.stringtolist(input_cleaned)
    # if any("show" in x for x in input if type(x)==str):
    sqlob : NQL = _inltosql(wordlist, context,verbose=verbose)
    return sqlob