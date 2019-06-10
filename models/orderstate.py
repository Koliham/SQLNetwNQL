class OrderState:

    # and sort it by ...


    #for things like "show the 10 highest, lowest...."



    # so directly after the term "show"

    def __init__(self):
        self.__limit = 0
        self.entity = ""
        self.ordercol = "" # required
        self.superlative = ""
        self.ascending = ""

    def __str__(self):
        if self.ordercol == "":
            return ""

        output = "ORDER BY "+self.ordercol
        if self.ascending != "":
            output += " "+self.ascending
        if self.limit >= 1:
            output += " LIMIT "+str(self.limit)
        return output

    @property
    def limit(self):
        return self.__limit

    @limit.setter
    def limit(self,limit):
        self.__limit = limit


    def inl(self,inline=False,question=False):
        startword = "what is" if question else "show"
        if self.ordercol == "":
            return ""

        # if limit is 1:
            # things like "show the highest ..."
            # or "show the ... for which COL is the highest

        # if there are more than 1 allowed
            # show the 10 highest
            # and sort them by

        # case 1: for which COL is the highest
        # colname, limit=1, asc
        if not inline:
            if self.limit==1:
                output = "for which " + self.ordercol + " is the "
                superlative = ""
                if self.superlative != "":
                    superlative = self.superlative
                elif self.ascending == "ASC":
                    superlative = "lowest"
                else:
                    superlative = "highest"
                output += superlative
                return output
            else:
                return "and sort them by " + self.ordercol if not question else "and sorted  by " + self.ordercol
        else:
            if self.limit ==1:
                output = startword+" the "
            else:
                output = startword+" the " + str(self.limit) + " "
            if self.superlative != "":
                superlative = self.superlative
            elif self.ascending == "ASC":
                superlative = "lowest"
            else:
                superlative = "highest"
            output += superlative + " " + self.ordercol if self.entity == "" else self.entity
            return output

        return "ERROR"

if __name__ == "__main__":
    print("starte")
