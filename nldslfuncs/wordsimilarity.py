# findsimilarindex: for a given word and a list of words
# return either the index, where the word occurs, e.g. "Apfel" occurs in  ["Banane","Kaese","Apfel","Birne"]
# at index 2.
# OR: find the index of the most similar word:
# e.g. most similar word to "Apfel" occurs for given list ["Banane","Apfelsine","Kakao","Birne"] at index 1
# threshold: If the similarity is below the thershold, return index -1
def findsimilarindex(value : str, entries : list, threshold = 0.0):
    if value in entries:
        return entries.index(value)
    else:
        return -1