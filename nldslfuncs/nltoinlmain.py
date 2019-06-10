#the main function for nl to inl-list
#Todo: Put in the algorithms to convert NL to INL
from models.context import Context
def nltoinl(input : str,Context : Context=None):
    return [(0.8,input)]