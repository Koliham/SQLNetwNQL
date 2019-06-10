from nldslfuncs.synonymreplacer import synonymreplace
from nltk.tokenize import word_tokenize
import shlex
def preprocessnl(input : str):
    # input = input.lower()
    # inllist = synonymreplace(words)  # replace words by their synonyms
    return input

def stringtolist(input : str):
    words = word_tokenize(input)  # not used, instead shlex
    input = input.replace(",", "")
    words = shlex.split(input)
    return words