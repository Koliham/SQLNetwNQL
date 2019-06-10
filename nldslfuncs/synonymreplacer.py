import nltk
from nltk.corpus import wordnet

#show XY WHERE XY FOR WHICH
showsynonym = [["what"],["which"]]
showword = wordnet.synset('show.v.01')
countsyns = [["how","many"],["how","much"],["how","often"],]

def synonymreplace(input:list):
    # return type: list of possible inl sentences with probabilites

    #detect synonyms for "show" hard coded
    stopwords = ["are","can","must"] # stopwords for the show case

    # show replacement
    for wordgroup in showsynonym:
        try: # instead of handling word length etc.
            if wordgroup == input[0:len(wordgroup)]:
                input[0:len(wordgroup)] = ["show"]
        except:
            pass
        input = [x for x in input if x not in stopwords]
    #check for count words

    for wordgroup in countsyns:
        try: # instead of handling word length etc.
            if wordgroup == input[0:len(wordgroup)]:
                input[0:len(wordgroup)] = ["count","the"]

        except:
            pass
        input = [x for x in input if x not in stopwords]



    return [[1.0,input]]


if __name__=="__main__":
    text = nltk.word_tokenize("how many times is the fuel propulsion is cng?")
    synonymreplace(text)