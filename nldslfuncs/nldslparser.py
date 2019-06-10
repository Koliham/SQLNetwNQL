import traceback

from models.column import Column
from models.context import Context
from models.nql import NQL
from models import inltoobj

from nldslfuncs.nltoinlmain import nltoinl


def nldslparse(input,sql=False):
    try:
        return nldslcompute(input,sql)
    except:
        return [{"suggestion":"Error Suggestion","chance":1.00,"result":traceback.format_exc()}]


def getcolumns():
    return ["time","flight","from","destination","airline","aircraft","status"]

def columnreplacer(wort: str, cols: list):
    #it checks, if the word is one of the columns and replaces it
    if wort.lower() in cols:
        return Column(wort)
    else:
        return wort




def nldslcompute(input : str,sql=False):
    context  = Context()
    suggestions = [] # the list of results in the end
    results = [] # a list of possible results = suggestions

    #if there is no entry, return special suggestion:
    if input == "":
        return [{"suggestion": "Please type in the Input", "chance": 1.0, "result": "nothing typed in yet"}]

    # the suggestions contain all possible solutions


    #get the list of existing columns
    columns = getcolumns()
    context.columns = columns # add it to the context
    context.entity = "flight"

    ## preprocessing
    # right now preprocessing is done in the inltosql function

    # the main function! Convert the NL to list of (p_i,INL_i), while p_i is the probability, that INL_i
    # is correct
    inllist : list = nltoinl(input)

    for inltuple in inllist:
        if sql:
            sqlob : NQL = NQL.fromsql(input)
        else:
            sqlob :NQL = inltoobj.inltosqlobj(inltuple[1], context)
        results.append((inltuple[0],sqlob.title,str(sqlob)))

    for e in results:
        suggestions.append({"suggestion":e[1],"chance":e[0],"result":e[2]})
    if len(results)==0:
        suggestions.append({"suggestion": "No Suggestions", "chance": 1.0, "result": "No matching suggestion found =("})

    return suggestions



    #convert string to a list of words

    # words = re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', input)


    #remove stopwords
    # #replace column words with column data type
    # words = [columnreplacer(word,columns) for word in words]




