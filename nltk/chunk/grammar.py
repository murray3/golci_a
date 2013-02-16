# -*- coding: utf-8 -*-
# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@seas.upenn.edu>
#         Jason Narad <jason.narad@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Basic data classes for representing context free grammars.  A
X{grammar} specifies which trees can represent the structure of a
given text.  Each of these trees is called a X{parse tree} for the
text (or simply a X{parse}).  In a X{context free} grammar, the set of
parse trees for any piece of a text can depend only on that piece, and
not on the rest of the text (i.e., the piece's context).  Context free
grammars are often used to find possible syntactic structures for
sentences.  In this context, the leaves of a parse tree are word
tokens; and the node values are phrasal categories, such as C{NP}
and C{VP}.

The L{ContextFreeGrammar} class is used to encode context free grammars.  Each
C{ContextFreeGrammar} consists of a start symbol and a set of productions.
The X{start symbol} specifies the root node value for parse trees.  For example,
the start symbol for syntactic parsing is usually C{S}.  Start
symbols are encoded using the C{Nonterminal} class, which is discussed
below.

A Grammar's X{productions} specify what parent-child relationships a parse
tree can contain.  Each production specifies that a particular
node can be the parent of a particular set of children.  For example,
the production C{<S> -> <NP> <VP>} specifies that an C{S} node can
be the parent of an C{NP} node and a C{VP} node.

Grammar productions are implemented by the C{Production} class.
Each C{Production} consists of a left hand side and a right hand
side.  The X{left hand side} is a C{Nonterminal} that specifies the
node type for a potential parent; and the X{right hand side} is a list
that specifies allowable children for that parent.  This lists
consists of C{Nonterminals} and text types: each C{Nonterminal}
indicates that the corresponding child may be a C{TreeToken} with the
specified node type; and each text type indicates that the
corresponding child may be a C{Token} with the with that type.

The C{Nonterminal} class is used to distinguish node values from leaf
values.  This prevents the grammar from accidentally using a leaf
value (such as the English word "A") as the node of a subtree.  Within
a C{ContextFreeGrammar}, all node values are wrapped in the C{Nonterminal} class.
Note, however, that the trees that are specified by the grammar do
B{not} include these C{Nonterminal} wrappers.

Grammars can also be given a more procedural interpretation.  According to
this interpretation, a Grammar specifies any tree structure M{tree} that
can be produced by the following procedure:

    - Set M{tree} to the start symbol
    - Repeat until M{tree} contains no more nonterminal leaves:
      - Choose a production M{prod} with whose left hand side
        M{lhs} is a nonterminal leaf of M{tree}.
      - Replace the nonterminal leaf with a subtree, whose node
        value is the value wrapped by the nonterminal M{lhs}, and
        whose children are the right hand side of M{prod}.

The operation of replacing the left hand side (M{lhs}) of a production
with the right hand side (M{rhs}) in a tree (M{tree}) is known as
X{expanding} M{lhs} to M{rhs} in M{tree}.
"""

import re

from nltk.internals import deprecated

#from probability import ImmutableProbabilisticMixIn
#from featstruct import FeatStruct, FeatDict, FeatStructParser, SLASH, TYPE

#################################################################
# Nonterminal
#################################################################

class Nonterminal(object):
    """
    A non-terminal symbol for a context free grammar.  C{Nonterminal}
    is a wrapper class for node values; it is used by
    C{Production}s to distinguish node values from leaf values.
    The node value that is wrapped by a C{Nonterminal} is known as its
    X{symbol}.  Symbols are typically strings representing phrasal
    categories (such as C{"NP"} or C{"VP"}).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two C{Nonterminal}s are considered equal if their
    symbols are equal.

    @see: L{ContextFreeGrammar}
    @see: L{Production}
    @type _symbol: (any)
    @ivar _symbol: The node value corresponding to this
        C{Nonterminal}.  This value must be immutable and hashable. 
    """
    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        @type symbol: (any)
        @param symbol: The node value corresponding to this
            C{Nonterminal}.  This value must be immutable and
            hashable. 
        """
        self._symbol = symbol
        self._hash = hash(symbol)

    def symbol(self):
        """
        @return: The node value corresponding to this C{Nonterminal}. 
        @rtype: (any)
        """
        return self._symbol

    def __eq__(self, other):
        """
        @return: True if this non-terminal is equal to C{other}.  In
            particular, return true iff C{other} is a C{Nonterminal}
            and this non-terminal's symbol is equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        try:
            return ((self._symbol == other._symbol) \
                    and isinstance(other, self.__class__))
        except AttributeError:
            return False

    def __ne__(self, other):
        """
        @return: True if this non-terminal is not equal to C{other}.  In
            particular, return true iff C{other} is not a C{Nonterminal}
            or this non-terminal's symbol is not equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        return not (self==other)

    def __cmp__(self, other):
        try: 
            return cmp(self._symbol, other._symbol)
        except: 
            return -1

    def __hash__(self):
        return self._hash

    def __repr__(self):
        """
        @return: A string representation for this C{Nonterminal}.
        @rtype: C{string}
        """
        if isinstance(self._symbol, basestring):
            return '%s' % (self._symbol,)
        else:
            return '%r' % (self._symbol,)

    def __str__(self):
        """
        @return: A string representation for this C{Nonterminal}.
        @rtype: C{string}
        """
        if isinstance(self._symbol, basestring):
            return '%s' % (self._symbol,)
        else:
            return '%r' % (self._symbol,)

    def __div__(self, rhs):
        """
        @return: A new nonterminal whose symbol is C{M{A}/M{B}}, where
            C{M{A}} is the symbol for this nonterminal, and C{M{B}}
            is the symbol for rhs.
        @rtype: L{Nonterminal}
        @param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        @type rhs: L{Nonterminal}
        """
        return Nonterminal('%s/%s' % (self._symbol, rhs._symbol))

def nonterminals(symbols):
    """
    Given a string containing a list of symbol names, return a list of
    C{Nonterminals} constructed from those symbols.  

    @param symbols: The symbol name string.  This string can be
        delimited by either spaces or commas.
    @type symbols: C{string}
    @return: A list of C{Nonterminals} constructed from the symbol
        names given in C{symbols}.  The C{Nonterminals} are sorted
        in the same order as the symbols names.
    @rtype: C{list} of L{Nonterminal}
    """
    if ',' in symbols: symbol_list = symbols.split(',')
    else: symbol_list = symbols.split()
    return [Nonterminal(s.strip()) for s in symbol_list]

#################################################################
# Productions
#################################################################

class Production(object):
    """
    A grammar production.  Each production maps a single symbol
    on the X{left-hand side} to a sequence of symbols on the
    X{right-hand side}.  (In the case of context-free productions,
    the left-hand side must be a C{Nonterminal}, and the right-hand
    side is a sequence of terminals and C{Nonterminals}.)
    X{terminals} can be any immutable hashable object that is
    not a C{Nonterminal}.  Typically, terminals are strings
    representing words, such as C{"dog"} or C{"under"}.

    @see: L{ContextFreeGrammar}
    @see: L{DependencyGrammar}
    @see: L{Nonterminal}
    @type _lhs: L{Nonterminal}
    @ivar _lhs: The left-hand side of the production.
    @type _rhs: C{tuple} of (C{Nonterminal} and (terminal))
    @ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, rhs):
        """
        Construct a new C{Production}.

        @param lhs: The left-hand side of the new C{Production}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{Production}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        if isinstance(rhs, (str, unicode)):
            raise TypeError('production right hand side should be a list, '
                            'not a string')
        self._lhs = lhs
        self._rhs = tuple(rhs)
        self._hash = hash((self._lhs, self._rhs))

    def lhs(self):
        """
        @return: the left-hand side of this C{Production}.
        @rtype: L{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{Production}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{Production}.
        @rtype: C{string}
        """
        str = '%s ->' % (self._lhs,)
        for elt in self._rhs:
            if isinstance(elt, Nonterminal):
                str += ' %s' % (elt,)
            else:
                str += ' %r' % (elt,)
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the
            C{Production}. 
        @rtype: C{string}
        """
        return '%s' % self

    def __eq__(self, other):
        """
        @return: true if this C{Production} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (isinstance(other, self.__class__) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)
                 
    def __ne__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        if not isinstance(other, self.__class__): return -1
        return cmp((self._lhs, self._rhs), (other._lhs, other._rhs))

    def __hash__(self):
        """
        @return: A hash value for the C{Production}.
        @rtype: C{int}
        """
        return self._hash


class DependencyProduction(Production):
    """
    A dependency grammar production.  Each production maps a single
    head word to an unordered list of one or more modifier words.
    """
    def __str__(self):
        """
        @return: A verbose string representation of the 
            C{DependencyProduction}.
        @rtype: C{string}
        """
        str = '\'%s\' ->' % (self._lhs,)
        for elt in self._rhs:
                str += ' \'%s\'' % (elt,)
        return str

#################################################################
# Grammars
#################################################################

class ContextFreeGrammar(object):
    """
    A context-free grammar.  A Grammar consists of a start state and a set
    of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.
    """
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{Production}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        self._start = start
        self._productions = productions
        self._lhs_index = {}
        self._rhs_index = {}
        for prod in self._productions:
            if prod._lhs not in self._lhs_index:
                self._lhs_index[prod._lhs] = []
            if prod._rhs and prod._rhs[0] not in self._rhs_index:
                self._rhs_index[prod._rhs[0]] = []
            self._lhs_index[prod._lhs].append(prod)
            if prod._rhs:
                self._rhs_index[prod._rhs[0]].append(prod)
        
    def start(self):
        return self._start

    # tricky to balance readability and efficiency here!
    # can't use set operations as they don't preserve ordering
    def productions(self, lhs=None, rhs=None):
        # no constraints so return everything
        if not lhs and not rhs:
            return self._productions

        # only lhs specified so look up its index
        elif lhs and not rhs:
            return self._lhs_index.get(lhs, [])

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(rhs, [])

        # intersect
        else:
            return [prod for prod in self._lhs_index.get(lhs,[])
                    if prod in self._rhs_index.get(rhs,[])]

    def check_coverage(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.
        If not, then raise an exception.
        """
        missing = [tok for tok in tokens
                   if len(self.productions(rhs=tok))==0]
        if missing:
            missing = ', '.join('%r' % (w,) for w in missing)
            raise ValueError("Grammar does not cover some of the "
                             "input words: %r." % missing)

    # [xx] does this still get used anywhere, or does check_coverage
    # replace it?
    def covers(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.

        @param tokens: the given list of tokens.
        @type tokens: a C{list} of C{string} objects.
        @return: True/False
        """
        for token in tokens:
            if len(self.productions(rhs=token)) == 0:
                return False
        return True

    def __repr__(self):
        return '<Grammar with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'Grammar with %d productions' % len(self._productions)
        str += ' (start state = %s)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        return str

class Grammar(ContextFreeGrammar):
    @deprecated("Use nltk.ContextFreeGrammar instead.")
    def __init__(self, *args, **kwargs):
        ContextFreeGrammar.__init__(self, *args, **kwargs)
        

class DependencyGrammar(object):
    """
    A dependency grammar.  A DependencyGrammar consists of a set of
    productions.  Each production specifies a head/modifier relationship
    between a pair of words.
    """
    def __init__(self, productions):
        """
        Create a new dependency grammar, from the set of C{Production}s.
        
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        self._productions = productions

    def contains(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    def __contains__(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    #   # should be rewritten, the set comp won't work in all comparisons
    # def contains_exactly(self, head, modlist):
    #   for production in self._productions:
    #       if(len(production._rhs) == len(modlist)):
    #           if(production._lhs == head):
    #               set1 = Set(production._rhs)
    #               set2 = Set(modlist)
    #               if(set1 == set2):
    #                   return True
    #   return False


    def __str__(self):
        """
        @return: A verbose string representation of the
            C{DependencyGrammar}
        @rtype: C{string}
        """
        str = 'Dependency grammar with %d productions' % len(self._productions)
        for production in self._productions:
            str += '\n  %s' % production
        return str
            
    def __repr__(self):
        """
        @return: A concise string representation of the
            C{DependencyGrammar}
        """
        return 'Dependency grammar with %d productions' % len(self._productions)
    

class StatisticalDependencyGrammar(object):
    """

    """

    def __init__(self, productions, events, tags):
        self._productions = productions
        self._events = events
        self._tags = tags

    def contains(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{StatisticalDependencyGrammar}
        @rtype: C{string}
        """
        str = 'Statistical dependency grammar with %d productions' % len(self._productions)
        for production in self._productions:
            str += '\n  %s' % production
        str += '\nEvents:'
        for event in self._events:
            str += '\n  %d:%s' % (self._events[event], event)
        str += '\nTags:'
        for tag_word in self._tags:
            str += '\n %s:\t(%s)' % (tag_word, self._tags[tag_word])
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the
            C{StatisticalDependencyGrammar}
        """
        return 'Statistical Dependency grammar with %d productions' % len(self._productions)


class WeightedGrammar(ContextFreeGrammar):
    """
    A probabilistic context-free grammar.  A Weighted Grammar consists
    of a start state and a set of weighted productions.  The set of
    terminals and nonterminals is implicitly specified by the
    productions.

    PCFG productions should be C{WeightedProduction}s.
    C{WeightedGrammar}s impose the constraint that the set of
    productions with any given left-hand-side must have probabilities
    that sum to 1.

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    @type EPSILON: C{float}
    @cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """
    EPSILON = 0.01

    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{WeightedProduction}s.

        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{Production}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        """
        ContextFreeGrammar.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-WeightedGrammar.EPSILON) < p <
                    (1+WeightedGrammar.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)

# Contributed by Nathan Bodenstab <bodenstab@cslu.ogi.edu>

def induce_pcfg(start, productions):
    """
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

    |                count(A -> B C)
    |  P(B, C | A) = ---------------       where * is any right hand side
    |                 count(A -> *)

    @param start: The start symbol
    @type start: L{Nonterminal}
    @param productions: The list of productions that defines the grammar
    @type productions: C{list} of L{Production}
    """

    # Production count: the number of times a given production occurs
    pcount = {}
    
    # LHS-count: counts the number of times a given lhs occurs
    lcount = {} 

    for prod in productions:
        lcount[prod.lhs()] = lcount.get(prod.lhs(), 0) + 1
        pcount[prod]       = pcount.get(prod,       0) + 1

    prods = [WeightedProduction(p.lhs(), p.rhs(),
                                prob=float(pcount[p]) / lcount[p.lhs()])
             for p in pcount]
    return WeightedGrammar(start, prods)




#################################################################
# Parsing Dependency Grammars
#################################################################

_PARSE_DG_RE = re.compile(r'''^\s*                # leading whitespace
                              ('[^']+')\s*        # single-quoted lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$''',            # zero or more copies
                             re.VERBOSE)
_SPLIT_DG_RE = re.compile(r'''('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)''')

def parse_dependency_grammar(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_dependency_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    return DependencyGrammar(productions)

def parse_dependency_production(s):
    if not _PARSE_DG_RE.match(s):
        raise ValueError, 'Bad production string'
    pieces = _SPLIT_DG_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = pieces[0].strip('\'\"')
    rhsides = [[]]
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])
        else:
            rhsides[-1].append(piece.strip('\'\"'))
    return [DependencyProduction(lhside, rhside) for rhside in rhsides]

