from collections import defaultdict
import logging, datetime, re, os
import cPickle as pickle
from google.appengine.api import memcache 
from google.appengine.api import taskqueue 
import json
from urllib import unquote
from urlparse import urlparse
from handlers import BaseRequestHandler
import nltk
from nltk.probability import DictionaryProbDist
from nltk.chunk.regexp import RegexpParser
import stemming
from stemming import porter2 as stemmer

cache_ver = 'green' # change if deploying new/modified pickle files

# Word tokenzier - should be moved into nltk dir
CONTRACTIONS2 = [re.compile(r"(?i)(.)('ll|'re|'ve|n't|'s|'m|'d)\b"),
                 re.compile(r"(?i)\b(can)(not)\b"),
                 re.compile(r"(?i)\b(D)('ye)\b"),
                 re.compile(r"(?i)\b(Gim)(me)\b"),
                 re.compile(r"(?i)\b(Gon)(na)\b"),
                 re.compile(r"(?i)\b(Got)(ta)\b"),
                 re.compile(r"(?i)\b(Lem)(me)\b"),
                 re.compile(r"(?i)\b(Mor)('n)\b"),
                 re.compile(r"(?i)\b(T)(is)\b"),
                 re.compile(r"(?i)\b(T)(was)\b"),
                 re.compile(r"(?i)\b(Wan)(na)\b")]
CONTRACTIONS3 = [re.compile(r"(?i)\b(Whad)(dd)(ya)\b"),
                 re.compile(r"(?i)\b(Wha)(t)(cha)\b")]
                 
def stem(word):
    s = stemmer.stem(word)
    return str(s)

def tokenize(text):
    for regexp in CONTRACTIONS2:
        text = regexp.sub(r'\1 \2', text)
    for regexp in CONTRACTIONS3:
        text = regexp.sub(r'\1 \2 \3', text)
    #replace elipses, and multiple - as | not a good idea to mark as space results in false positive NP's
    text=re.sub('[\.\-]{2,}','|',text)
    # Separate most punctuation
    text = re.sub(r"([^\w\.\'\-\/,&@])", r' \1 ', text)
    text = re.sub(r"http : ",r"http:",text) # added to deal with urls
    #print text
    # Separate commas if they're followed by space.
    # (E.g., don't separate 2,500)
    text = re.sub(r"(,\s)", r' \1', text)
    # Separate single quotes if they're followed by a space.
    text = re.sub(r"('\s)", r' \1', text)
    # Separate periods that come before newline or end of string.
    text = re.sub('\. *(\n|$)', ' . ', text)
    return text.split()

# Parser
def makeParser(
grammar = r"""
  NP: {<JJ.*>?<NN.*>+}
"""):
    return RegexpParser(grammar)

# reinitialize memcache every 20 minutes through a cron job just to make sure classifier and sentence tokenizer stay in memory
def flushcache():
    if memcache.flush_all():
        logging.info('Cache has been flushed')
        return True
    else:
        logging.info('Error flushing cache')
        return False

class Flush(BaseRequestHandler):
    def get(self):
        if flushcache():
            self.response.out.write('Cache has been flushed')
            taskqueue.add(url='/initc',method='GET')
        else:
            self.response.out.write('Error flushing cache')
    
class InitClassifier(BaseRequestHandler):
    def get(self):
        # TODO skip if alredy initialized.
        # only way to initialize is call flush or first ever call to initc after app deploy
        # forums say need to use a verions tag from os.environ
        minit = 0
        labels, mapping, alwayson = pickle.load( open(os.path.join(os.path.dirname(__file__), "tagger-map-weight-merge.pickle"), 'rb'))
        if not memcache.get('tagger'):
            memcache.set('tagger', (labels, alwayson))
        #memcache allows only 1MB writes so need to break up mapping     
        mlen = len(mapping)
        for i in range(0, mlen, 20000):
            upper = i+20000 if i +20000 < mlen else mlen
            #try:
            keys = memcache.set_multi(dict( [(key[0]+str(key[1])+key[2], j) for key,j in mapping.items()[i:upper] ]), time=2552000, namespace=cache_ver, key_prefix=cache_ver )
            #except Exception,e:
            #    logging.info((key,j,i))
            #    raise
            if keys:
                logging.info(str(len(keys)) + ' not set')
        

def Reply(text):
    brain = memcache.get('brain')
    tok = memcache.get('tok')
    parsr = memcache.get('parsr')
    if not tok:
        tok = pickle.load(open(os.path.join(os.path.dirname(__file__), "english.pickle")))
        memcache.set('tok', tok)
    #text = self.request.get("text")
    #if len(text) > "":
    #    self.error(500)
    #sentence tokenize            
    ts = tok.tokenize(text)
    #word tokenize
    tw=[]
    for i in ts:
        tw.extend(tokenize(i))
    # tag parts of speech 
    tagd = tag(tw)
    if not tagd:
        rep="Classifier needs to be initialized."
        return rep
    # parse
    if not parsr:
        parsr = makeParser()
        memcache.set('parsr', parsr)
    ps = parsr.parse( tagd )
    pr=[" ".join([j[0] for j in i.leaves()]) for i in ps.subtrees(lambda a: a.node=="NP")]
    return pr


# PoS Tagger - should be moved into nltk dir
# tag(["Hello",",","how","are","you","doing","today","?"])
def tag(tokens):
        tags = []
        mapping={}
        try:
            labels, alwayson  = memcache.get('tagger')
        except Exception,e:
            return None
        #weights = cPickle.load( open(os.path.join(os.path.dirname(__file__), "weights.pickle"), 'rb'))
        for i in range(len(tokens)):
            tags.append(tag_one(tokens, i, tags, labels, alwayson))
        return zip(tokens, tags)

def tag_one(tokens, index, history, labels, alwayson):
        featureset = feature_detector(tokens, index, history)
        tag = prob_classify(featureset, labels, alwayson).max()
        return tag

def prob_classify(featureset, labels, alwayson):
        prob_dict = {}
        allkeys = []
        groups = {}
        for label in labels:
            lblkeys=[]
            for fname, fval in featureset.items():
                try:
                    allkeys.append(fname+ str(fval)+ label)
                    lblkeys.append(fname+ str(fval)+ label)
                except Exception,e:
                    continue
            groups[label] = lblkeys
        # get all weights in one get - this will be called for each token                
        weights = memcache.get_multi(allkeys,namespace=cache_ver, key_prefix=cache_ver)
        for label in labels:
            feature_vector = []
            for i in groups[label]:
                if i in weights: #  ?? maybe get_multi didnt return 
                    feature_vector.append((weights[i], 1))
            if alwayson and label in alwayson:
                feature_vector.append((alwayson[label], 1))
            total = 0.0
            for (weight, f_val) in feature_vector:
                total += weight * f_val
            prob_dict[label] = total
        # Normalize the dictionary to give a probability distribution
        return DictionaryProbDist(prob_dict, log=True, normalize=True)

def encode(featureset, label, alwayson):
        # Inherit docs.
        encoding = []
        # Convert input-features to joint-features:
        keys = [(fname+ str(fval)+ label) for fname, fval in featureset.items()]
        # Known feature name & value:
        weights = memcache.get_multi(keys,namespace=cache_ver, key_prefix=cache_ver)
        for i in weights:
            encoding.append((weights[i], 1))
        # Add always-on features:
        if alwayson and label in alwayson:
            encoding.append((alwayson[label], 1))
        return encoding

def feature_detector(tokens, index, history):
        word = tokens[index]
        if index == 0:
            prevword = prevprevword = None
            prevtag = prevprevtag = None
        elif index == 1:
            prevword = tokens[index-1].lower()
            prevprevword = None
            prevtag = history[index-1]
            prevprevtag = None
        else:
            prevword = tokens[index-1].lower()
            prevprevword = tokens[index-2].lower()
            prevtag = history[index-1]
            prevprevtag = history[index-2]

        if re.match('[0-9]+(\.[0-9]*)?|[0-9]*\.[0-9]+$', word):
            shape = 'number'
        elif re.match('\W+$', word):
            shape = 'punct'
        elif re.match('[A-Z][a-z]+$', word):
            shape = 'upcase'
        elif re.match('[a-z]+$', word):
            shape = 'downcase'
        elif re.match('\w+$', word):
            shape = 'mixedcase'
        else:
            shape = 'other'
            
        features = {
            'prevtag': prevtag,
            'prevprevtag': prevprevtag,
            'word': word,
            'word.lower': word.lower(),
            'suffix3': word.lower()[-3:],
            'suffix2': word.lower()[-2:],
            'suffix1': word.lower()[-1:],
            'prevprevword': prevprevword,
            'prevword': prevword,
            'prevtag+word': '%s+%s' % (prevtag, word.lower()),
            'prevprevtag+word': '%s+%s' % (prevprevtag, word.lower()),
            'prevword+word': '%s+%s' % (prevword, word.lower()),
            'shape': shape,
            }
        return features
        
def textchk(text,keywds):
    tx=[]
    words=text.split()
    for x in range(len(words)):
        for y in range(len(words)+1):
            if words[x:y]:
                tmpwd=str(words[x:y])
                for kw in keywds:
                    if not tmpwd.find(stem(kw)) == -1:
                        tx.append(" ".join(words[x:y]))
                        break
    return tx
        
class textmatch(BaseRequestHandler):       
    def get(self):
        toggle=str(self.request.get('tgl'))
        tb1=str(self.request.get('r1'))
        tb1=tb1.replace ("_", " ")
        tb2=str(self.request.get('r2'))
        tb2=tb2.replace ("_", " ")
        tb3=str(self.request.get('r3'))
        tb3=tb3.replace ("_", " ")
        #data='the banks should pay higher taxes'
        if toggle == 0: InitClassifier()
        #nlp.InitClassifier()
        #text = nlp.tokenize(data)
        kwds1 = Reply(tb1)
        kwds2 = Reply(tb2)
        kwds3 = Reply(tb3)
        #message="The banks should pay more tax, they where bailed out by the state and now citizens are paying for this through austerity"
        #textbag 1 - the contention
        sentences1=tb1.split('.')
        subsents1=[subsent1.split(',') for subsent1 in sentences1]
        subsent1=[item1 for sublist1 in subsents1 for item1 in sublist1]
        #kwds=['austerity','tax','banks','citizens']
        sents1=[]
        for f1 in subsent1:
            sents1.append(textchk(f1,kwds1))
        sents1=[item1 for sublist1 in sents1 for item1 in sublist1]
        #texbag2 - a reason
        sentences2=tb2.split('.')
        subsents2=[subsent2.split(',') for subsent2 in sentences2]
        subsent2=[item2 for sublist2 in subsents2 for item2 in sublist2]
        #kwds=['austerity','tax','banks','citizens']
        sents2=[]
        for f2 in subsent2:
            sents2.append(textchk(f2,kwds2))
        sents2=[item2 for sublist2 in sents2 for item2 in sublist2]
        #texbag3 - a reason
        sentences3=tb3.split('.')
        subsents3=[subsent3.split(',') for subsent3 in sentences3]
        subsent3=[item3 for sublist3 in subsents3 for item3 in sublist3]
        #kwds=['austerity','tax','banks','citizens']
        sents3=[]
        for f3 in subsent3:
            sents3.append(textchk(f3,kwds3))
        sents3=[item3 for sublist3 in sents3 for item3 in sublist3]
        sents4=[]
        sents5=[]
        for i in sents1:
            for j in sents2:
                if i == j:
                    sents4.append(i)
        for i in sents1:
            for j in sents3:
                if i == j:
                    sents4.append(i)
        sents4=sorted(set(sents4))
        for i in sents2:
            for j in sents3:
                if i == j:
                    sents5.append(i)
        sents5=sorted(set(sents5))
        #a=['tb1','tb2','tb3']
        from collections import defaultdict
        tb = defaultdict(list)
        tb['tb1']=sents4
        tb['tb2']=sents4
        tb['tb3']=sents5
        self.response.out.write(json.dumps(tb))

    
##############################################

    
