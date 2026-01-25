## Introduction

Natural Language processing



## Summary


### NLP 

http://masatohagiwara.net/100-nlp-papers/

Stemming and Lemmatization
https://medium.com/geekculture/introduction-to-stemming-and-lemmatization-nlp-3b7617d84e65     Stemming vs. Lemmatization
https://www.analyticssteps.com/blogs/what-stemming-and-lemmatization-nlp
https://www.guru99.com/stemming-lemmatization-python-nltk.html
 
 
https://radimrehurek.com/gensim/       NLP Topic Modelling for Humans
 
import nltk
from nltk.stem import WordNetLemmatizer
wordnet_lemmatizer = WordNetLemmatizer()
text = "studies studying cries cry"
tokenization = nltk.word_tokenize(text)
for w in tokenization:
                print("Lemma for {} is {}".format(w, wordnet_lemmatizer.lemmatize(w)))  
                                


## References

http://masatohagiwara.net/100-nlp-papers/


