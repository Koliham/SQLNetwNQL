from models.column import Column
from pattern.text.en import inflect

from nltk.stem import WordNetLemmatizer


def isplural(word):
    wnl = WordNetLemmatizer()
    lemma = wnl.lemmatize(word, 'n')
    plural = True if word is not lemma else False
    return plural, lemma


class SelectState:
    aggwords = {"sum of all": "SUM", "average": "AVG", "lowest": "MIN", "highest": "MAX"}
    aggwords_inl = {"SUM": "sum of all","AVG": "average","MIN": "lowest" ,"MAX" :"highest" }

    def __init__(self):
        self.selcols = []
        self.entity = "table"
        self.agg = ""

    def __str__(self):
        output = "SELECT "

        if len(self.selcols) ==1 and (self.entity != "" and self.selcols[0]==self.entity):
            if self.agg=="COUNT":
                output += "COUNT(*)"
            else:
                output += "* "
        else:
            #if it shall count the numbers, then check if there is just one column
            if self.agg!="" and len(self.selcols)==1:
                output += self.agg+"("+self.selcols[0]+")"
            else:
                othercols = False
                for col in self.selcols:
                    if othercols:
                        output += ", "
                    output += col if " " not in col else "'"+col+"'" #for multi words objects like "New York"
                    othercols = True

        return output+" FROM "+self.entity

    def inl(self,question=False):
        # add apostrophe, if the select entries contain column names with multiple words with spaces
        columns = [ "'"+x+"'" if (" " in x and x[0]!="'" and x[-1]!="'") else x for x in self.selcols]

        #if question or not
        count_start = "how many " if question else "count the "
        count_end = " are there" if question else ""

        #case for counting:
        if self.agg=="COUNT":
            if len(columns) == 1 and (self.entity != "" and columns[0] == self.entity):
                if self.entity[-1]=="s": #it must be already plural?
                    return count_start+self.entity+count_end
                else:
                    return count_start+inflect.pluralize(self.entity)+count_end
            elif len(columns)==1:
                if columns[0][-1]=="s": #it must be already plural?
                    return count_start+self.entity+count_end
                else:
                    return count_start+inflect.pluralize(columns[0])+count_end

        showstart = "what is the " if question else "show the "
        output = "what is the " if question else "show the "

        #aggregation case.
        if self.agg != "" and len(self.selcols) == 1:
            colname = columns[0]
            if self.agg in self.aggwords_inl.keys():
                aggregation = self.aggwords_inl[self.agg]
                #special case for SUM: I have to use plural: example: "sum of all prices" instead of "sum of all price"
                if self.agg =="SUM":
                    plurayesno, singular = isplural(colname)
                    if not plurayesno:
                        colname = inflect.pluralize(colname)

                output += aggregation + " " + colname
                return output

        if len(columns) ==1 and (self.entity != "" and columns[0]==self.entity):
            return showstart+self.entity
        else:
            if len(columns) == 1:
                output += columns[0]
            elif len(columns) == 0:
                return ""
            else:
                for col in columns[:-1]:
                    output += col+", "
                output = output[:-2]
                output += " and "+columns[-1]
            return output

if __name__ == "__main__":
    print("starte")
    a = SelectState()
    a.selcols = ["time", "arrival","destination"]
    print(a)
    print()
    b = SelectState()
    b.entity = "flight"
    print(b)
    print("###")
    print(a.inl())
    print(b.inl())
    print("Plural of: apple")
    print(inflect.pluralize("apple"))