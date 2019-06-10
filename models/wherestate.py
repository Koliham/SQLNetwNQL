
from nldslfuncs import stringfuncs
class WhereState:

    def __init__(self) -> None:
        self.wherestates = []
        self.conj = "AND"

    def relationtranslate(self,rel):

        if rel =="<":
            return "is lower than"
        elif rel =="<=":
            return "is below"
        elif rel ==">":
            return "is higher than"
        elif rel == ">=":
            return "is above"
        elif rel == "!=":
            return "is not"
        else:
            return "is"

    def __str__(self):
        #where [reference] operator [value]
        output = "WHERE "
        if len(self.wherestates)==0:
            output = ""
        else:
            addand = False
            for col in self.wherestates:
                if addand:
                    output += " "+self.conj+" "

                # the apostrophe will be added anyway, so it can be removed.
                if str(col[0])[-1] != "'" and str(col[0])[0]!="'" and " " in str(col[0]):
                    reference = "'"+str(col[0])+"'"
                else:
                    reference = str(col[0])
                value = str(col[2])
                #check if it is a number or not
                if not stringfuncs.isnum(value): #if it is a string, wrap the string with apostrophe:
                    # ...WHERE col=abc => ...WHERE col='abc'
                    if len(value)>=2 and value[0]!="'" and value[-1] !="'": # if apostrophe is there, skip
                        pass
                    else:
                        value = "'"+value+"'"

                value = "'"+value+"'" if (not stringfuncs.isnum(value) and value[0]!="'" and value[-1] !="'") else value
                #check if the column name has space, so put apostrophe ' between
                output += reference+" "+str(col[1]) +" "+value
                addand = True
        return output

    def inl(self):
        output = "where "
        if len(self.wherestates)==0:
            return ""
        else:
            for i,col in enumerate(self.wherestates):
                if i==len(self.wherestates)-1 and len(self.wherestates)>1:
                    output +=" and " if self.conj=="AND" else " or "
                elif len(self.wherestates)>1 and i != 0:
                    output +=", "

                ref = str(col[0])
                value = str(col[2])
                # check if the column name has space, so put apostrophe ' between
                if " " in str(col[0]) and "'"!=str(col[0][0]) and "'"!=str(col[0][-1]):
                    ref = "'"+str(col[0])+"'"
                if " " in str(col[2]) and "'"!=str(col[2][0]) and "'"!=str(col[2][-1]):
                    value = "'"+str(col[2])+"'"
                output += ref+" "+self.relationtranslate(str(col[1]))+" "+value
        return output.strip()

if __name__ == "__main__":
    print("starte")
    a = WhereState()
    a.wherestates = [["arrival",">=",12],["from","=","New York"],["aaa","<=","bbb"]]
    a.conj = "OR"
    print(a)
    print(a.inl())
    print()
    b = WhereState()
    b.conj = "OR"
    b.wherestates = [["arrival",">=",12],["from","=","New York"]]
    print(b)
    print("###")
    print(a.inl())
    print(b.inl())