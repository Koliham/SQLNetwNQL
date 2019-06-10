class RelationDict:
    rel = {"<":"is lower than","<=": "is below",">":"is higher than",">=":"is above","!=":"is not","=":"is"}

    def sqltonl(self,key):
        return self.rel[key]


    def nltosql(self,wordlist : list):

        #relation must always start with "is"
        if wordlist[0] != "is":
            return None

        # Todo: Special case for between
        # # "special case for between"
        # if len(wordlist)>

        for key, value in self.rel.items(): # check for 3 word overlap
            valueparts = value.split(" ")
            if len(valueparts)==3 and valueparts == wordlist:
                return key, 3

        for key, value in self.rel.items(): # check for 2 word overlap
            valueparts = value.split(" ")
            if len(valueparts)==2 and valueparts[0:2] == wordlist[0:2]:
                return key, 2

        for key, value in self.rel.items(): # check for 1 word overlap for "is"
            valueparts = value.split(" ")
            if len(valueparts)==1 and valueparts[0] == wordlist[0]:
                return key, 1

# a = []
# a.append(["is","higher","than"]) # 3 word
# a.append(["is","above","sdad"]) # 2 word
# a.append(["is","asfas","and"]) # 1 word
# a.append(["is","below"]) # 2 word
# a.append(["is"]) # 1 word
#
# for eintrag in a:
#     erg = RelationDict().nltosql(eintrag)
#     print(eintrag,"\t",erg)