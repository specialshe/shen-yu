import copy, logging, operator
from collections import defaultdict, deque
import heapq, re, functools

class SpecialHypRef(object):
    def __init__(self, ref):
        self.ref = ref
    def __eq__(self, other):
        if not isinstance(other, SpecialHypRef):
            return False
        return self.ref == other.ref
    def __hash__(self):
        return hash(self.ref)
    def convert_to_ken_format(self, convert_pos):
        return "[%i] |||"%(convert_pos(self.ref))
    def demux_all(self, convert_hyp_to_ken_format):
        return (self,)
    def split(self, hyp_indexer):
        return (self,[])

def toposort2(data):
    """Dependencies are expressed as a dictionary whose keys are items
and whose values are a set of dependent items. Output is a list of
sets in topological order. The first set consists of items with no
dependences, each subsequent set consists of items that depend upon
items in the preceeding sets.

>>> print '\\n'.join(repr(sorted(x)) for x in toposort2({
...     2: set([11]),
...     9: set([11,8]),
...     10: set([11,3]),
...     11: set([7,5]),
...     8: set([7,3]),
...     }) )
[3, 5, 7]
[8, 11]
[2, 9, 10]

"""

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)
    # Find all items that don't depend on anything.
    extra_items_in_deps = functools.reduce(set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    data.update(dict((item,set()) for item in extra_items_in_deps))
    while True:
        ordered = set(item for item, dep in data.iteritems() if not dep)
        if not ordered:
            break
        yield ordered
        data = dict( (item, dep - ordered)
                for item, dep in data.iteritems()
                    if item not in ordered)
    assert not data, "Cyclic dependencies exist among these items:\n%s" % '\n'.join(repr(x) for x in data.iteritems())
 
def toposort_faster_modify_input(data):
    # assume no self dependencies.
    # Find all items that don't depend on anything.
    # extra_items_in_deps = functools.reduce(set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    # data.update(dict((item,set()) for item in extra_items_in_deps))
    ordered = set(item for item, dep in data.iteritems() if not dep)
    while True:
        if not ordered:
            break
        yield ordered
        for item in ordered:
            del data[item]
        new_ordered = set()
        for item in data:
            data[item] -= ordered
            if len(data[item]) == 0:
                new_ordered.add(item)
        ordered = new_ordered
    assert not data, "Cyclic dependencies exist among these items:\n%s" % '\n'.join(repr(x) for x in data.iteritems())
 
class AugmentedPattern(object): 
    def __init__(self, pattern, root, parent, inner, outer):
        self.pattern = tuple(pattern)
        self.root = root
        self.parent = parent
        self.inner = inner
        self.outer = tuple(outer)
        self.check_consistency()
        
    def __hash__(self):
        return hash(self.pattern)
    
    def check_consistency(self):
        assert self.root in self.pattern
        assert self.parent not in self.pattern
        assert len(set(self.outer) & set(self.pattern)) == 0
        assert set(self.inner).issubset(set(self.pattern))
        assert len(set(reduce(lambda x,y:(x+y), self.inner.values(), []))) == len(reduce(lambda x,y:(x+y), self.inner.values(), []))
        assert set(reduce(lambda x,y:(x+y), self.inner.values(), [])) == set(self.outer), "%r != %r"%(self.inner, self.outer)
        assert len(set(self.pattern)) == len(self.pattern)
        assert len(set(self.outer)) == len(self.outer)
        
    def __eq__(self, other):
        if not isinstance(other, AugmentedPattern):
            return False
        if self.pattern == other.pattern:
            assert self.root == other.root
            assert self.parent == other.parent
            assert self.outer == other.outer
            assert self.inner == other.inner, "(%r / %r) %r != %r"%(self.pattern, other.pattern, self.inner, other.inner)
            return True
        else:
            return False
    
    def __str__(self):
        return "P<%i:%i|%r|%r|%r>"%(self.root, self.parent, self.pattern, self.inner, self.outer)
        
    __repr__ = __str__
    
    def mergeWithInner(self, inner):
        assert inner.root in self.outer
        assert inner.parent in self.inner
        logging.debug("merge self:%s with inner:%s", self, inner)
        new_pattern = sorted(self.pattern + inner.pattern)
        new_root = self.root
        new_parent = self.parent
        
        new_outer = self.outer + inner.outer
        new_outer.remove(inner.root)
        new_outer.sort()
        
        new_inner = copy.deepcopy(self.inner)
        new_inner[inner.parent].remove(inner.root)
        if len(new_inner[inner.parent]) == 0:
            del new_inner[inner.parent]
        new_inner.update(inner.inner)
        
        return AugmentedPattern(new_pattern, new_root, new_parent, new_inner, new_outer)
        
    def isComplete(self):
        return len(self.outer) == 0
        
    def size(self):
        return len(self.pattern)
        
    def get_left_most_outer_frontier_index(self):
            #print self.outer
            return self.outer[0]


class Additional(object):
    def __init__(self, cnum, dpnd, prelist, postlist):
        assert type(dpnd) is int
        assert type(cnum) is int
        self.cnum = cnum
        self.dpnd = dpnd
        self.prelist = tuple(prelist)
        self.postlist = tuple(postlist)
    def __str__(self):
        return "A<%i:%i:%r:%r>"%(self.cnum, self.dpnd, self.prelist, self.postlist)
    def __hash__(self):
        #print str(self)
        return hash( (self.cnum, self.dpnd, self.prelist, self.postlist) )
    def __eq__(self, other):
        return self.cnum == other.cnum and self.dpnd == other.dpnd and self.prelist == other.prelist and self.postlist == other.postlist
    def check_consistency(self, dpnd):
        assert self.cnum >= 0
        assert self.dpnd >= 0
        assert all( 0<= pos <= self.dpnd for pos in self.prelist),"%s"%self
        assert all( self.dpnd < pos for pos in self.postlist),"%s"%self
        
        assert all( all( pos<=ix<=self.dpnd for ix in dpnd[pos:self.dpnd] ) for pos in self.prelist),"%s %r"%(self, dpnd)
        
        assert all( all( self.dpnd<=ix< pos for ix in dpnd[self.dpnd+1:pos] ) for pos in self.postlist), "%s %r"%(self, dpnd)
        
            
    
    def update_after_insertion_at(self, insertion_point, parent, offset):
        original_dpnd = self.dpnd
        
        def new_pos(pos):
            if pos < insertion_point:
                return (pos,)
            elif pos > insertion_point:
                return (pos+offset,)
            else:
                if parent < original_dpnd:
                    return (pos+offset,)
                elif parent > original_dpnd:
                    return (pos,)
                else:
                    return (pos, pos+offset)
                    
        if insertion_point<= self.dpnd:
            self.dpnd  += offset

        self.prelist = tuple(x for pos in self.prelist for x in new_pos(pos))
        self.postlist = tuple(x for pos in self.postlist for x in new_pos(pos))
        
    def update_after_replacement_at(self, insertion_point, offset):
        
        def new_pos(pos):
            if pos <= insertion_point:
                return pos
            else:
                return pos+offset                    
                    
        self.dpnd = new_pos(add.dpnd)
        self.prelist = tuple(new_pos(pos) for pos in self.prelist)
        self.postlist = tuple(new_pos(pos) for pos in self.postlist)
        
class AdditionalsList(object):
    def __init__(self, lst = None):
        self.lst = lst if lst is not None else []
    def __str__(self):
        return " ".join(str(add) for add in self.lst)
    def pop(self, cnum):
        for add in self.lst:
            if add.cnum == cnum:
                self.lst.remove(add)
                return add
        assert(False) # not found
    
    def shift_by_if_higher(self, offset, threshold):
        for i in range(len(self.lst)):
            self.lst[i] = copy.deepcopy(self.lst[i])
            add = self.lst[i]
            add.dpnd = shift_by_if_higher([add.dpnd], offset, threshold)[0]
            add.prelist = shift_by_if_higher(add.prelist, offset, threshold)
            add.postlist = shift_by_if_higher(add.postlist, offset, threshold)
    
    def update_after_insertion_at(self, insertion_point, parent, offset):
        for i in range(len(self.lst)):
            self.lst[i] = copy.deepcopy(self.lst[i])
            add = self.lst[i]
            add.update_after_insertion_at(insertion_point, parent, offset)
    
    def update_after_replacement_at(self, insertion_point, offset):
        for i in range(len(self.lst)):
            self.lst[i] = copy.deepcopy(self.lst[i])
            add = self.lst[i]
            add.update_after_replacement_at(insertion_point, offset)
    
    def __iter__(self):
        return iter(self.lst)
    
    def copy(self):
        return copy.deepcopy(self)
        
    def push(self, add):
        self.lst.append(add)
        
    def __eq__(self, other):
        return len(self.lst) == len(other.lst) and all(other.lst[i] == self.lst[i] for i in range(len(self.lst)))
        
    def __hash__(self):
        return hash(tuple(self.lst))
    
    def merge(self, other):
        return AdditionalsList(self.lst + other.lst)
        
    def check_consistency(self, dpnd):
        for add in self.lst:
            add.check_consistency(dpnd)
        
def find_span(pos_root, dpnd):
    assert pos_root < len(dpnd)
    inv_dpnd = defaultdict(list)
    for pos, parent in enumerate(dpnd):
        inv_dpnd[parent].append(pos)
        
    set_of_pos = set()
    queue = [pos_root]
    while len(queue) > 0:
        pos = queue.pop()
        queue += inv_dpnd[pos]
        assert pos not in set_of_pos
        set_of_pos.add(pos)
        
    list_of_pos = sorted(list(set_of_pos))
    start = list_of_pos[0]
    end = list_of_pos[-1] + 1
    assert len(list_of_pos) == end - start, "%r %i | %r %i-%i"%(dpnd, pos_root, list_of_pos, start, end)
    return start, end
    
def order_pos_by_depth(pos_list, dpnd):
    def compute_depth(pos):
        if dpnd[pos] == -1:
            return 0
        else:
            return 1 + compute_depth(dpnd[pos])
    return sorted(pos_list, key = compute_depth, reverse = True)
    
    
class DestructuredAdditional(object):
    def __init__(self, cnum, prelist, postlist):
        assert type(cnum) is int
        self.cnum = cnum
        self.prelist = tuple(prelist)
        self.postlist = tuple(postlist)

    def __str__(self):
        return "A<%i:%r:%r>"%(self.cnum, self.prelist, self.postlist)

    def __hash__(self):
        #print str(self)
        return hash( (self.cnum, self.prelist, self.postlist) )

    def __eq__(self, other):
        return self.cnum == other.cnum and self.prelist == other.prelist and self.postlist == other.postlist

    def copy(self):
        return DestructuredAdditional(self.cnum, self.prelist, self.postlist)

    def copy_and_remove_pos(self, pos):
        new_prelist = tuple(i for i in self.prelist if i!=pos)
        new_postlist = tuple(i for i in self.postlist if i!= pos)
        if len(new_prelist) == 0 and len(new_postlist) == 0 :
            return None
        return DestructuredAdditional(self.cnum, 
            new_prelist, new_postlist
            )
            
    def copy_and_remove_pos_not_always_copy(self, pos):
        if pos not in self.prelist and pos not in self.postlist:
            return self
        new_prelist = tuple(i for i in self.prelist if i!=pos)
        new_postlist = tuple(i for i in self.postlist if i!= pos)
        if len(new_prelist) == 0 and len(new_postlist) == 0 :
            return None
        return DestructuredAdditional(self.cnum, 
            new_prelist, new_postlist
            )

    def point_to(self, pos):
        return (pos in self.prelist) or (pos in self.postlist)

    @staticmethod
    def convert_from_additional(add):
        return DestructuredAdditional(add.cnum, add.prelist, add.postlist)
        
# should be read-only
class DestructuredAdditionalsList(object):
    def __init__(self, lst = None):
        self.lst = lst if lst is not None else []
        
    def __len__(self):
        return len(self.lst)
        
    def get_add_pointing_to(self, pos):
        res = []
        for add in self.lst:
            if pos in add.prelist:
                res.append(("E", add))
            elif pos in add.postlist:
                res.append(("O", add))
        return res
        
    def point_to(self, pos):
        return any(add.point_to(pos) for add in self.lst)
        
    def copy_and_remove(self, cnum):
        res = DestructuredAdditionalsList()
        for add in self.lst:
            if add.cnum != cnum:
                res.lst.append(add)
        return res

    # def copy_and_update_order_rule(self, cnum):
        # res = DestructuredAdditionalsList()
        # for add in self.lst:
            # if add.cnum != cnum:
                # res.lst.append(add.filter_only_before_cnum(cnum))
        # return res
        
    def copy_and_remove_pos(self, pos):
        res = DestructuredAdditionalsList()
        for add in self.lst:
            new_add = add.copy_and_remove_pos_not_always_copy(pos)
            if new_add is None:
                return None
            res.lst.append(new_add)
        return res
        
    def __str__(self):
        return " ".join(str(add) for add in self.lst)
        
    def pop(self, cnum):
        for add in self.lst:
            if add.cnum == cnum:
                self.lst.remove(add)
                return add
        assert(False) # not found
       
    def __iter__(self):
        return iter(self.lst)
    
    def copy(self):
        return copy.deepcopy(self)
        
    def push(self, add):
        self.lst.append(add)
        
    def __eq__(self, other):
        return len(self.lst) == len(other.lst) and all(other.lst[i] == self.lst[i] for i in range(len(self.lst)))
        
    def __hash__(self):
        return hash(tuple(self.lst))
        
    @staticmethod
    def convert_from_additional_list(add_list):
        lst = []
        for add in add_list.lst:
            lst.append(DestructuredAdditional.convert_from_additional(add))
        return DestructuredAdditionalsList(lst)
    
def de_option(w):
    assert w.endswith("*")
    assert len(w) >=2
    return w[:-1]
    
def is_optional(w):
    return not isref(w) and w.endswith("*")
    
class RefType(object):
    def __init__(self, id):
        self.id = id
    def __eq__(self, other):
        if not isinstance(other, RefType):
            return False
        return self.id == other.id
    def __hash__(self):
        return hash(self.id)
    def __str__(self):
        return "{%s}"%str(self.id)
    __repr__ = __str__
    
def mkref(ref):
    if isref(ref):
        return ref
    return RefType(ref) #"[X%s]"%str(ref)
    
def isref(ref):
    return isinstance(ref, RefType)
    
    
def rename_ref_and_freeze(hyplist, map_to_newref, map_to_newref2):
    return frozenset(hyp.no_add_rename_all_ref_2dic(map_to_newref, map_to_newref2) for hyp in hyplist)
    
class HypCompressor(object):
    def __init__(self):
        self.ref_to_hyp = {}
        self.hypset_to_ref = {}
        self.current_base_ref_hyp_list = set()
        self.max_nb_ref = 0
        self.sorted_ref = []
        
    def print_self(self):
        for ref, hypset in self.ref_to_hyp.iteritems():
            print ref,len(hypset)," : ",
            for hyp in hypset:
                print hyp,
            print

    def newref(self):
        self.max_nb_ref+=1
        ref = mkref("HC%i"%self.max_nb_ref)
        self.sorted_ref.append(ref)
        return ref
        
    def store_hypset(self, hypset):
        if hypset not in self.hypset_to_ref:
            ref_new = self.newref()
            self.hypset_to_ref[hypset] = ref_new
            self.ref_to_hyp[ref_new] = hypset
        return self.hypset_to_ref[hypset]
        
    def merge(self, hypexp, map_root_to_newref):
        #sorted_ref, inv_rel_graph = hypexp.get_topologically_sorted_ref()
        sorted_ref = hypexp.get_topologically_sorted_ref_reachabe_from_base()
        map_to_newref = {}# copy.deepcopy(map_root_to_newref)
        for ref in sorted_ref:
            if ref == hypexp.init_ref:
                continue
            assert ref not in map_root_to_newref, "%s %r"%(ref, map_root_to_newref)
            hypset = rename_ref_and_freeze(hypexp.ref_to_hyp[ref], map_to_newref, map_root_to_newref)
            assert  all(len(hyp.t_string)>0 for hyp in hypset), " ".join(str(hyp) for hyp in hypset)
            new_ref = self.store_hypset(hypset)
            map_to_newref[ref] = new_ref
        # for hyppp in hypexp.ref_to_hyp[hypexp.init_ref]:
            # print hyppp
        base_hypset = set(hyp.no_add_rename_all_ref_2dic(map_to_newref, map_root_to_newref) for hyp in hypexp.ref_to_hyp[hypexp.init_ref] if  len(hyp.t_string) > 0) #remove base empty
        assert  all(len(hyp.t_string)>0 for hyp in base_hypset), " ".join(str(hyp) for hyp in base_hypset)
        #assert len(base_hypset) == 1, " ".join(str(hyp) for hyp in base_hypset)
        self.current_base_ref_hyp_list|=base_hypset
    
    def freeze_and_reset_base_ref(self):
        hypset = frozenset(self.current_base_ref_hyp_list)
        new_ref = self.store_hypset(hypset)
        self.current_base_ref_hyp_list = set()
        #print "freezed",hypset,new_ref
        return new_ref
        
    def get_ref_in_topo_order(self):
        relation_graph = {}
        for ref, hypset in self.ref_to_hyp.iteritems():
            relation_graph[ref] = set()
            for hyp in hypset:
                for ref2 in hyp.no_add_ref_list():
                    relation_graph[ref].add(ref2)
        sorted_list_by_level = list(toposort_faster_modify_input(relation_graph))
        #self.print_self()
        assert len(sorted_list_by_level[-1]) == 1, "%r"%(sorted_list_by_level,) #should be only one which depend on everything else ...
        sorted_list = [x for lst in sorted_list_by_level for x in lst]
        return sorted_list
        
    def get_ref_in_topo_order_from_root_ref(self, root_ref):
        reachable = set([root_ref])
        processed = set()
    
        relation_graph = {}
        
        while len(reachable)>0:
            ref = reachable.pop()
            processed.add(ref)
            relation_graph[ref] = set()
            hypset = self.ref_to_hyp[ref]
            #print ref, hypset
            if not isinstance(hypset,set ) and not isinstance(hypset,frozenset ):
                hypset = set([hypset])
            for hyp in hypset:
                for ref2 in hyp.no_add_ref_list():
                    relation_graph[ref].add(ref2)
                    if ref2 not in processed:
                        reachable.add(ref2)
        print "created relation_graph"
        sorted_list_by_level = list(toposort_faster_modify_input(relation_graph))
        #self.print_self()
        assert len(sorted_list_by_level[-1]) == 1, "%r"%(sorted_list_by_level,) #should be only one which depend on everything else ...
        sorted_list = [x for lst in sorted_list_by_level for x in lst]
        print "topo sorted"
        return sorted_list

    def get_ref_in_topo_order_from_root_ref_faster(self, root_ref):
        reachable = set([root_ref])
        processed = set()
        
        while len(reachable)>0:
            ref = reachable.pop()
            processed.add(ref)
            hypset = self.ref_to_hyp[ref]
            #print ref, hypset
            if not isinstance(hypset,set ) and not isinstance(hypset,frozenset ):
                hypset = set([hypset])
            for hyp in hypset:
                for ref2 in hyp.no_add_ref_list():
                    if ref2 not in processed:
                        reachable.add(ref2)
                        
        res = [ref for ref in self.sorted_ref if ref in processed]
        return res
        
    def clean_impossible_and_remove_redirections(self, topo_sorted_ref, real_root_ref):
    
        # sorted_ref, inv_rel_graph = self.get_topologically_sorted_ref()
        cleaned_sorted_ref = []
        impossible_ref = set()
        redirection_map = {}
        new_real_root_ref = None
        for ref in topo_sorted_ref:
            #print "considering", ref, redirection_map
            newset = set()
            for hyp in self.ref_to_hyp[ref]:
                lst_subref = hyp.no_add_ref_list()
                if len(set(lst_subref)&impossible_ref) > 0:
                    #self.ref_to_hyp[ref].remove(hyp)
                    #print "discarded", hyp, impossible_ref
                    continue
                else:
                    #print "rename", hyp, "to", 
                    new_hyp = hyp.no_add_rename_some_ref(redirection_map)
                    #print new_hyp
                    newset.add(new_hyp)
            self.ref_to_hyp[ref] = frozenset(newset)
            if len(self.ref_to_hyp[ref]) == 0:
                impossible_ref.add(ref)
                continue
            elif len(self.ref_to_hyp[ref]) == 1:
                hyp = list(self.ref_to_hyp[ref])[0]
                ref2 = hyp.is_redirect()
                #print "is_redirect?", ref2
                if ref2 is not None:
                    redirection_map[ref] = ref2
                    if ref == real_root_ref:
                        assert new_real_root_ref == None
                        new_real_root_ref = ref2
                    continue
            cleaned_sorted_ref.append(ref)
        return cleaned_sorted_ref, new_real_root_ref
        
    def write_as_ken_format(self, out, real_root_ref):
        print "preparing writing"
        sorted_list = self.get_ref_in_topo_order_from_root_ref_faster(real_root_ref)
        assert sorted_list[-1] == real_root_ref, "%s %r"%(real_root_ref, sorted_list)
        #print "orig:",sorted_list
        #print real_root_ref
        print "filtering"
        sorted_list, real_root_ref = self.clean_impossible_and_remove_redirections(sorted_list, real_root_ref)
        #print "clea:",sorted_list
        #print real_root_ref
        #print "cleaned:"
        #self.print_self()
        topo_map = dict( (j,i) for i,j in enumerate(sorted_list) )
        #print real_root_ref
        #print topo_map
        
        def convert_pos(i):
            return topo_map[i]
        
        total_edge_count = sum(len(self.ref_to_hyp[ref]) for ref in sorted_list)
        
        print "start writing"
        out.write("%i %i\n"%(len(sorted_list)+1, total_edge_count+1)) #+1 for final rule
        for ref in sorted_list:
            hypset = self.ref_to_hyp[ref]
            out.write("%i\n"%len(hypset))
            for hyp in hypset:
                assert(len(hyp.t_string) > 0), hyp
                out.write(hyp.convert_to_ken_format(convert_pos))
                out.write("\n")
        out.write("1\n<s> [%i] </s> ||| \n"%(len(sorted_list)-1))
    
class HypExpander(object):
    def __init__(self, initial_hyp):
        self.max_ref = 0
        self.inversely_sorted_ref = []
        
        self.init_ref = self.newref()
        self.ref_to_hyp = {self.init_ref:initial_hyp}
        self.hyp_to_ref = {initial_hyp:self.init_ref}
        self.not_expanded_yet = set()
        self.not_expanded_yet.add(self.init_ref)
        
        
    def newref(self):
        ref = mkref("E%i"%self.max_ref)
        self.max_ref += 1
        self.inversely_sorted_ref.append(ref)
        return ref
    
    def __len__(self):
        return len(self.ref_to_hyp)
        
    def expand(self, make_orig_ref):
        while len(self.not_expanded_yet) > 0:
            ref = self.not_expanded_yet.pop()
            hyp = self.ref_to_hyp[ref]
            right_part = hyp.split_right(self, make_orig_ref)
            assert all( (isinstance(hypx, NoAddDestructuredHypothesis) or  
                            isinstance(hypx, SimplestDestructuredHypothesis)) for hypx in right_part)
            self.ref_to_hyp[ref] = list(right_part)
            
    def developp(self):
        init_hyp_list = self.ref_to_hyp[self.init_ref]
        assert len(init_hyp_list) == 1
        init_hyp = init_hyp_list[0]
        for hyp in init_hyp.no_add_expand(self):
            yield hyp
            
    def get_idx(self, hyp):
        #assert isinstance(hyp, NoAddDestructuredHypothesis) or isinstance(hyp, SimplestDestructuredHypothesis), str(hyp) 
        if hyp not in self.hyp_to_ref:
            ref = self.newref()
            self.hyp_to_ref[hyp] = ref
            self.ref_to_hyp[ref] = hyp
            self.not_expanded_yet.add(ref)
        return self.hyp_to_ref[hyp]
    
    def get_hyp(self, ref):
        return self.ref_to_hyp[ref]
    
    def clean_ref(self, ref):
        hyplist = self.ref_to_hyp[ref]
        if len(hyplist) == 0:
            return "noempty"
        assert len(hyplist) > 0
        assert len(hyplist) == len(set(hyplist)), " ".join(str(hyp) for hyp in hyplist)
        hyplist_non_empty = [hyp for hyp in hyplist if not hyp.is_empty()]
        if len(hyplist_non_empty) < len(hyplist):
            if len(hyplist_non_empty) == 0:
                del self.ref_to_hyp[ref]
                return "allempty"
            else:
                self.ref_to_hyp[ref] = hyplist_non_empty
                return "someempty"
        else:
            return "noempty"
            
            
    def get_topologically_sorted_ref(self):
        rel_graph = {}
        inv_rel_graph = {}
        for ref, hyp_list in self.ref_to_hyp.iteritems():
            rel_graph[ref] = set()
            for hyp in hyp_list:
                for w in hyp.t_string:
                    if isref(w) and w in self.ref_to_hyp:
                        rel_graph[ref].add(w)
                        inv_rel_graph.setdefault(w, set()).add(ref)
        sorted_ref_by_level = toposort_faster_modify_input(rel_graph)
        sorted_ref = [x for lvl in sorted_ref_by_level for x in lvl] 
        return sorted_ref, inv_rel_graph
        
    def get_topologically_sorted_ref_faster(self):
        inv_rel_graph = {}
        for ref, hyp_list in self.ref_to_hyp.iteritems():
            for hyp in hyp_list:
                for w in hyp.t_string:
                    if isref(w) and w in self.ref_to_hyp:
                        inv_rel_graph.setdefault(w, set()).add(ref)
        return self.inversely_sorted_ref[::-1], inv_rel_graph
        
    def get_topologically_sorted_ref_reachabe_from_base(self):
        reachable = set([self.init_ref])
        processed = set()
    
        relation_graph = {}
        
        while len(reachable)>0:
            ref = reachable.pop()
            processed.add(ref)
            relation_graph[ref] = set()
            assert ref in self.ref_to_hyp, "%s"%(ref,)
            hyplist = self.ref_to_hyp[ref]
            #print ref, hypset
            if not isinstance(hyplist,list ) and not isinstance(hypset,tuple ):
                hyplist = [hyplist]
            for hyp in hyplist:
                for ref2 in hyp.no_add_ref_list():
                    if ref2 in self.ref_to_hyp:
                        relation_graph[ref].add(ref2)
                        if ref2 not in processed:
                            reachable.add(ref2)
        sorted_ref_by_level = toposort_faster_modify_input(relation_graph)
        sorted_ref = [x for lvl in sorted_ref_by_level for x in lvl]
        return sorted_ref
        
    def get_topologically_sorted_ref_reachabe_from_base_faster(self):
        reachable = set([self.init_ref])
        processed = set()
    
        while len(reachable)>0:
            ref = reachable.pop()
            processed.add(ref)
            assert ref in self.ref_to_hyp, "%s"%(ref,)
            hyplist = self.ref_to_hyp[ref]
            #print ref, hypset
            if not isinstance(hyplist,list ) and not isinstance(hypset,tuple ):
                hyplist = [hyplist]
            for hyp in hyplist:
                for ref2 in hyp.no_add_ref_list():
                    if ref2 in self.ref_to_hyp:
                        if ref2 not in processed:
                            reachable.add(ref2)
        sorted_ref = [ref for ref in reversed(self.inversely_sorted_ref) if ref in processed]
        return sorted_ref
        
    # def get_ref_in_topo_order_from_root_ref(self, root_ref):
        # reachable = set([root_ref])
        # processed = set()
    
        # relation_graph = {}
        
        # while len(reachable)>0:
            # ref = reachable.pop()
            # processed.add(ref)
            # relation_graph[ref] = set()
            # for hypset in self.ref_to_hyp[ref]:
                # #print ref, hypset
                # if not isinstance(hypset,set ) and not isinstance(hypset,frozenset ):
                    # hypset = set([hypset])
                # for hyp in hypset:
                    # for ref2 in hyp.no_add_ref_list():
                        # relation_graph[ref].add(ref2)
                        # if ref2 not in processed:
                            # reachable.add(ref2)
                    
        # sorted_list_by_level = list(toposort_faster_modify_input(relation_graph))
        # self.print_self()
        # assert len(sorted_list_by_level[-1]) == 1, "%r"%(sorted_list_by_level,) #should be only one which depend on everything else ...
        # sorted_list = [x for lst in sorted_list_by_level for x in lst]
        # return sorted_list

        
    def remove_empty_production(self, remove_unique_ref = False):
                    
        sorted_ref, inv_rel_graph = self.get_topologically_sorted_ref()
        
        for ref in sorted_ref:
            case = self.clean_ref(ref)
            #print ref, case
            if case == "allempty":
                for ref2 in inv_rel_graph[ref]:
                    hyp_list2 = self.ref_to_hyp[ref2]
                    for i in range(len(hyp_list2)):
                        hyp2 = hyp_list2[i]
                        mod_hyp = hyp2.no_add_remove_ref(ref)
                        if mod_hyp is not None:
                            hyp_list2[i] = mod_hyp
                    
            elif case =="someempty":
                for ref2 in inv_rel_graph[ref]:
                    hyp_list2 = self.ref_to_hyp[ref2]
                    #new_hyp_to_add = []
                    for i in range(len(hyp_list2)):
                        hyp2 = hyp_list2[i]
                        mod_hyp = hyp2.no_add_remove_ref(ref)
                        if mod_hyp is not None:
                            hyp_list2.append(mod_hyp)
                    #self.ref_to_hyp[ref2] = hyp_list2 + tuple(new_hyp_to_add)
            elif case =="noempty":
                pass
            else:
                assert False
                
            if remove_unique_ref:
                if ref != self.init_ref:
                    if ref in self.ref_to_hyp:
                        if len(self.ref_to_hyp[ref]) == 1:
                            unique_hyp = list(self.ref_to_hyp[ref])[0]
                            #print "removing unique",ref,unique_hyp
                            del self.ref_to_hyp[ref]
                            for ref2 in inv_rel_graph[ref]:
                                hyp_list2 = self.ref_to_hyp[ref2]
                                for i in range(len(hyp_list2)):
                                    hyp2 = hyp_list2[i]
                                    mod_hyp = hyp2.no_add_insert_at_ref(ref, unique_hyp)
                                    if mod_hyp is not None:
                                        if (mod_hyp not in hyp_list2[:i]) and (mod_hyp not in hyp_list2[i+1:]):
                                            hyp_list2[i] = mod_hyp
                                        else:
                                            hyp_list2[i] = None
                                self.ref_to_hyp[ref2] = [x for x in hyp_list2 if x is not None]
                        
                # else:
                    # base_hyplist = self.ref_to_hyp[ref]
                    # for i in range(len(base_hyplist)):
                        
                    # assert(has_no_add(unique_hyp))
                    # if len(unique_hyp.t_string) == 1:
                        # if isref(unique_hyp.t_string[0]):
                            # ref2 = unique_hyp.t_string[0]
                            # for hyp2 in self.ref_to_hyp[ref2]:
                                # unique_hyp.
                
            # if len(self.ref_to_hyp[ref]) == 1:
                # for ref2 in inv_rel_graph[ref]:
                    # hyp_list2 = self.ref_to_hyp[ref2]
                    # for i in range(len(hyp_list2)):
                        # hyp2 = hyp_list2[i]
                        # mod_hyp = hyp2.remove_ref(ref)
                        # if mod_hyp is not None:
                            # hyp_list2[i] = mod_hyp
                            
                            
    # def remove_simple_redirections(self):
        # for 

def all_unique(lst):
    return len(lst) == len(set(lst))
        
class NoAddDestructuredHypothesis(object):
    def __init__(self, t_string, features):
        assert(isinstance(t_string, tuple))
        self.t_string = t_string
        self.features = features
        #assert all_unique([w for w in t_string if isref(w)]), str(t_string)
        self.h = None
        
    def split_right(self, hyp_indexer, make_orig_ref):
        if len(self.t_string) == 0:
            return (make_hyp_of_correct_type_no_add(self.t_string, self.features),)
        elif self.last_is_optional():
            
            first_hyp = SimplestDestructuredHypothesis(
                self.t_string[:-1]
                )
                
            if first_hyp.is_empty():
                hyp_with = make_hyp_of_correct_type_no_add(
                    (de_option(self.t_string[-1]),),
                    self.features
                    )
                
                hyp_without = make_hyp_of_correct_type_no_add(
                    (),
                    self.features
                    )
            else:
                ref = hyp_indexer.get_idx(first_hyp)
            
                hyp_with = make_hyp_of_correct_type_no_add(
                    ( mkref(ref),) + (de_option(self.t_string[-1]),),
                    self.features
                    )
                
                hyp_without = make_hyp_of_correct_type_no_add(
                    ( mkref(ref),),
                    self.features
                    )
            return (hyp_with, hyp_without)
            
            
            
        else:
            pos = self.get_start_right_grounded_seq()
            
            if pos == 0:
                return (make_hyp_of_correct_type_no_add(self.t_string, self.features),)
            
            first_hyp = SimplestDestructuredHypothesis(
                self.t_string[:pos]
                ) 
            
            ref = hyp_indexer.get_idx(first_hyp)
            #print ( mkref(ref),), self.t_string[pos:]
            hyp_front = make_hyp_of_correct_type_no_add(
                ( mkref(ref),) + self.t_string[pos:],
                self.features
                )
            
            return (hyp_front,)
            
    def no_add_ref_list(self):
        res = [w for w in self.t_string if isref(w)]
        #assert len(res) == len(set(res)), str(self)
        return res
        
    def no_add_rename_all_ref(self, map_to_newref):
        new_t_string = []
        for w in self.t_string:
            if isref(w):
                assert w in map_to_newref
                new_t_string.append(map_to_newref[w])
            else:
                new_t_string.append(w)
                
        return NoAddDestructuredHypothesis(
                        tuple(new_t_string),
                        self.features
                        )
    
    def no_add_rename_all_ref_2dic(self, map_to_newref, map_to_newref2):
        new_t_string = []
        for w in self.t_string:
            if isref(w):
                if w in map_to_newref:
                    new_t_string.append(map_to_newref[w])
                elif w in map_to_newref2:
                    new_t_string.append(map_to_newref2[w])
                else:
                    assert False
            else:
                new_t_string.append(w)
                
        return NoAddDestructuredHypothesis(
                        tuple(new_t_string),
                        self.features
                        )
    
    def no_add_rename_some_ref(self, map_to_newref):
        new_t_string = []
        for w in self.t_string:
            if isref(w) and w in map_to_newref:
                new_t_string.append(map_to_newref[w])
            else:
                new_t_string.append(w)
                
        return NoAddDestructuredHypothesis(
                        tuple(new_t_string),
                        self.features
                        )  
                        
    def no_add_remove_ref(self, ref):
        if ref not in self.t_string:
            return None
        new_t_string = tuple(w for w in self.t_string if w != ref)
        assert len(new_t_string) == len(self.t_string) -1
        return NoAddDestructuredHypothesis(new_t_string, 
                self.features)
            
    def no_add_expand(self, hyp_indexer):
        ref = self.get_one_ref()
        if ref is None:
            yield self
        else:
            for hyp in hyp_indexer.get_hyp(ref):
                for hyp2 in self.no_add_expand_at(ref, hyp).no_add_expand(hyp_indexer):
                    yield hyp2
        
        
    def no_add_expand_at(self, ref, hyp):
        for i,w in enumerate(self.t_string):
            if w == ref:
                return NoAddDestructuredHypothesis(
                    self.t_string[:i]+ hyp.t_string + self.t_string[i+1:], {})
        assert False
        
        
    def __eq__(self, other):
        if not isinstance(other, NoAddDestructuredHypothesis):
            return False
        return (self.t_string == other.t_string and
                        self.features ==other.features)
          
    def is_redirect(self):
        if len (self.features) > 0 or len(self.t_string) !=1:
            return None
        ref = self.t_string[0]
        if not isref(ref):
            return None
        return ref
            
    def convert_to_ken_format(self, convert_pos):
        res = []
        for word in self.t_string:
            if isref(word):
                ref_id = convert_pos(word)
                res.append("[%i]"%ref_id)
            else:
                res.append(word)
        res.append("|||")
        for name, val in self.features.iteritems():
            res.append("%s=%f"%(name, val))
        return " ".join(res)
        
    def is_empty(self):
        return (len(self.t_string) == 0 and
                        len(self.features) == 0 )
          
    def __str__(self):
        return "%s<%r|%r>"%("HNA", self.t_string, self.features)
    
    def __hash__(self):
        if self.h is None:
            self.h = hash((self.t_string, frozenset(self.features.iteritems())))
        return self.h
        
    def last_is_optional(self):
        return is_optional(self.t_string[-1])
        
    def get_start_right_grounded_seq(self):
        for pos in range(len(self.t_string)+1)[::-1]:
            if pos>0 and is_optional(self.t_string[pos-1]):
                return pos
        return 0
        
    def no_add_insert_at_ref(self, ref, hyp):
        if ref not in self.t_string:
            return None
        
        new_tuple = []
        found_ref = False
        for w in self.t_string:
            if w != ref:
                new_tuple.append(w)
            else:
                assert not found_ref
                found_ref = True
                new_tuple += list(hyp.t_string)
        assert found_ref
        
        if isinstance(hyp, SimplestDestructuredHypothesis):
            return NoAddDestructuredHypothesis(tuple(new_tuple), self.features)
        elif isinstance(hyp, NoAddDestructuredHypothesis):
            new_features = {}
            for key, val in self.features.iteritems():
                new_features[key] = val
            for key, val in hyp.features.iteritems():
                if key in new_features:
                    new_features[key] += val
                else:
                    new_features[key] = val
            return NoAddDestructuredHypothesis(tuple(new_tuple), new_features)
        else:
            assert False
     
def has_no_add(hyp):
    if isinstance(hyp, SimplestDestructuredHypothesis) or isinstance(hyp, NoAddDestructuredHypothesis):
        return True
    if isinstance(hyp, DestructuredHypothesis):
        return len(hyp.additionals.lst) == 0
    assert False
     
   
class SimplestDestructuredHypothesis(object):
    def __init__(self, t_string):
        assert(isinstance(t_string, tuple))
        self.t_string = t_string
        self.h = None
        
    def __str__(self):
        return "%s<%r>"%("HS", self.t_string)
        
    def no_add_insert_at_ref(self, ref, hyp):
        if ref not in self.t_string:
            return None
        
        new_tuple = []
        found_ref = False
        for w in self.t_string:
            if w != ref:
                new_tuple.append(w)
            else:
                assert not found_ref
                found_ref = True
                new_tuple += list(hyp.t_string)
        assert found_ref
        
        if isinstance(hyp, SimplestDestructuredHypothesis):
            return SimplestDestructuredHypothesis(tuple(new_tuple))
        elif isinstance(hyp, NoAddDestructuredHypothesis):
            return NoAddDestructuredHypothesis(tuple(new_tuple), hyp.features)
        else:
            assert False
            
            
    def split_right(self, hyp_indexer, make_orig_ref):
        if len(self.t_string) == 0:
            return (self,)
        elif self.last_is_optional():
            
            first_hyp = SimplestDestructuredHypothesis(
                self.t_string[:-1]
                )
                
            if first_hyp.is_empty():
                hyp_with = SimplestDestructuredHypothesis(
                    (de_option(self.t_string[-1]),)
                    )
                
                hyp_without = SimplestDestructuredHypothesis(
                    ()
                    )
            else:
                ref = hyp_indexer.get_idx(first_hyp)
            
                hyp_with = SimplestDestructuredHypothesis(
                    ( mkref(ref),) + (de_option(self.t_string[-1]),)
                    )
                
                hyp_without = SimplestDestructuredHypothesis(
                    ( mkref(ref),)
                    )
            return (hyp_with, hyp_without)

        else:
            pos = self.get_start_right_grounded_seq()
            
            if pos == 0:
                return (self,)
            
            first_hyp = SimplestDestructuredHypothesis(
                self.t_string[:pos]
                ) 
            
            ref = hyp_indexer.get_idx(first_hyp)
            #print ( mkref(ref),), self.t_string[pos:]
            hyp_front = SimplestDestructuredHypothesis(
                ( mkref(ref),) + self.t_string[pos:]
                )
            
            return (hyp_front,)  
        
        
    def last_is_optional(self):
        return is_optional(self.t_string[-1])
        
    def get_start_right_grounded_seq(self):
        for pos in range(len(self.t_string)+1)[::-1]:
            if pos>0 and is_optional(self.t_string[pos-1]):
                return pos
        return 0
        
    def no_add_ref_list(self):
        res = [w for w in self.t_string if isref(w)]
        #assert len(res) == len(set(res))
        return res
        
    def no_add_rename_all_ref(self, map_to_newref):
        new_t_string = []
        for w in self.t_string:
            if isref(w):
                assert w in map_to_newref
                new_t_string.append(map_to_newref[w])
            else:
                new_t_string.append(w)
                
        return SimplestDestructuredHypothesis(
                        tuple(new_t_string)
                        )
    
    def no_add_rename_all_ref_2dic(self, map_to_newref, map_to_newref2):
        new_t_string = []
        for w in self.t_string:
            if isref(w):
                if w in map_to_newref:
                    new_t_string.append(map_to_newref[w])
                elif w in map_to_newref2:
                    new_t_string.append(map_to_newref2[w])
                else:
                    assert False
            else:
                new_t_string.append(w)
                
        return SimplestDestructuredHypothesis(
                        tuple(new_t_string)
                        )
    
    def no_add_rename_some_ref(self, map_to_newref):
        new_t_string = []
        for w in self.t_string:
            if isref(w) and w in map_to_newref:
                new_t_string.append(map_to_newref[w])
            else:
                new_t_string.append(w)
                
        return SimplestDestructuredHypothesis(
                        tuple(new_t_string)
                        )  
                        
    def no_add_remove_ref(self, ref):
        if ref not in self.t_string:
            return None
        new_t_string = tuple(w for w in self.t_string if w != ref)
        assert len(new_t_string) == len(self.t_string) -1
        return SimplestDestructuredHypothesis(new_t_string)
            
    def no_add_expand(self, hyp_indexer):
        ref = self.get_one_ref()
        if ref is None:
            yield self
        else:
            for hyp in hyp_indexer.get_hyp(ref):
                for hyp2 in self.no_add_expand_at(ref, hyp).no_add_expand(hyp_indexer):
                    yield hyp2
        
        
    def no_add_expand_at(self, ref, hyp):
        for i,w in enumerate(self.t_string):
            if w == ref:
                return SimplestDestructuredHypothesis(
                    self.t_string[:i]+ hyp.t_string + self.t_string[i+1:])
        assert False
        
    def __eq__(self, other):
        if not isinstance(other, SimplestDestructuredHypothesis):
            return False
        return self.t_string == other.t_string
                        
    def __hash__(self):
        if self.h is None:
            self.h = hash(self.t_string)
        return self.h
        
    def is_empty(self):
        return len(self.t_string) == 0
        
    def is_redirect(self):
        if len(self.t_string) !=1:
            return None
        ref = self.t_string[0]
        if not isref(ref):
            return None
        return ref
            
    def convert_to_ken_format(self, convert_pos):
        res = []
        for word in self.t_string:
            if isref(word):
                ref_id = convert_pos(word)
                res.append("[%i]"%ref_id)
            else:
                res.append(word)
        res.append("|||")
        return " ".join(res)
        
def make_hyp_of_correct_type(t_string, add, feat):
    if len(add) > 0:
        return DestructuredHypothesis(t_string, add, feat)
    else:
        return make_hyp_of_correct_type_no_add(t_string, feat)
        
def make_hyp_of_correct_type_no_add(t_string, feat):
    if len(feat) == 0:
        return SimplestDestructuredHypothesis(t_string)
    else:
        return NoAddDestructuredHypothesis(t_string, feat)

emptyAddList = DestructuredAdditionalsList()
    
class DestructuredHypothesis(object):
    def __init__(self, t_string, additionals, features):
        assert(isinstance(t_string, tuple))
        self.t_string = t_string
        self.additionals = additionals
        self.features = features
        self.h = None
        
    def __str__(self):
        return "%s<%r|%s|%r>"%("H", self.t_string, self.additionals, self.features)
    
    def __hash__(self):
        if self.h is None:
            self.h = hash((self.t_string, self.additionals, frozenset(self.features.iteritems())))
        return self.h
        
    def get_one_ref(self):
        for w in self.t_string:
            if isref(w):
                return w
        return None
        
    def is_empty(self):
        return (len(self.t_string) == 0 and len(self.additionals) == 0 and
                        len(self.features) == 0 )
        
    def __eq__(self, other):
        if not isinstance(other, DestructuredHypothesis):
            return False
        return (self.t_string == other.t_string and
                    self.additionals == other.additionals and
                        self.features ==other.features)
        
    @staticmethod
    def convert_from_hypothesis(hyp, t_string_to_ref_func, make_original_ref):
        if isinstance(hyp, SpecialHypRef):
            ref = make_original_ref(hyp.ref)
            new_t_string = (ref,)
            return DestructuredHypothesis(new_t_string, 
                        DestructuredAdditionalsList() ,{})
        else:
            new_t_string = []
            for w in hyp.t_string:
                new_t_string.append(t_string_to_ref_func(w))
            return DestructuredHypothesis(tuple(new_t_string), 
                        DestructuredAdditionalsList.convert_from_additional_list(hyp.additionals) ,hyp.features)
        

    
    def last_is_optional(self):
        return is_optional(self.t_string[-1])
    
    def get_start_right_grounded_seq(self):
        for pos in range(len(self.t_string)+1)[::-1]:
            if self.additionals.point_to(pos) or (pos>0 and is_optional(self.t_string[pos-1])):
                return pos
        return 0
    
    def split_linear_from_right(self, make_orig_ref):
        # queue = [self]
        # while len(queue) == 0:
            # hyp = queue.pop()
            # for (left, right) in hyp.split_right():
                # queue.append(left)
        hypexp = HypExpander(self)
        hypexp.expand(make_orig_ref)
        return hypexp
                

    def get_add_pointing_to_end(self):
        return self.additionals.get_add_pointing_to(len(self.t_string))
                
    def split_right(self, hyp_indexer, make_orig_ref):
        add_end = self.get_add_pointing_to_end()
        if len(add_end) == 0:
            if len(self.t_string) == 0:
                assert len(self.additionals.lst) == 0, self
                return (make_hyp_of_correct_type(self.t_string, self.additionals, self.features),)
            elif self.last_is_optional():
                
                first_hyp = make_hyp_of_correct_type(
                    self.t_string[:-1],
                    self.additionals,
                    {}
                    )
                    
                if first_hyp.is_empty():
                    hyp_with = make_hyp_of_correct_type_no_add(
                        (de_option(self.t_string[-1]),),
                        self.features
                        )
                    
                    hyp_without = make_hyp_of_correct_type_no_add(
                        (),
                        self.features
                        )
                else:
                    ref = hyp_indexer.get_idx(first_hyp)
                
                    hyp_with = make_hyp_of_correct_type_no_add(
                        ( mkref(ref),) + (de_option(self.t_string[-1]),),
                        self.features
                        )
                    
                    hyp_without = make_hyp_of_correct_type_no_add(
                        ( mkref(ref),),
                        self.features
                        )
                return (hyp_with, hyp_without)
                
                
                
            else:
                pos = self.get_start_right_grounded_seq()
                
                if (pos == 0) and len(self.additionals) == 0:
                    return (make_hyp_of_correct_type_no_add(self.t_string, self.features),)
                
                first_hyp = make_hyp_of_correct_type(
                    self.t_string[:pos],
                    self.additionals,
                    {}
                    ) 
                
                ref = hyp_indexer.get_idx(first_hyp)
                #print ( mkref(ref),), self.t_string[pos:]
                hyp_front = make_hyp_of_correct_type_no_add(
                    ( mkref(ref),) + self.t_string[pos:],
                    self.features
                    )
                
                return (hyp_front,)

        else:
            list_first = []
            
            max_cnum = max(add.cnum for pre_or_post,add in add_end)
            for pre_or_post, add in add_end:
                if add.cnum != max_cnum:
                    continue
                ref_add = make_orig_ref(add.cnum, pre_or_post)
                if ref_add is not None:
                    updated_additionals = self.additionals.copy_and_remove(add.cnum)
                    if updated_additionals is not None:
                        first_hyp = make_hyp_of_correct_type(
                            self.t_string,
                            updated_additionals,
                            {}
                        )
                        
                        if first_hyp.is_empty():
                            hyp_add= make_hyp_of_correct_type_no_add(
                                (ref_add,),
                                self.features
                            )
                        else:
                            
                            ref = hyp_indexer.get_idx(first_hyp)
                        
                        
                            hyp_add = make_hyp_of_correct_type_no_add(
                                (mkref(ref), ref_add),
                                self.features
                            )
                            
                        list_first.append(hyp_add)
                
            if len(self.t_string) > 0:
                new_add_for_no_add = self.additionals.copy_and_remove_pos(len(self.t_string))
                if new_add_for_no_add is not None:
                    no_add_used_hyp = make_hyp_of_correct_type(
                        self.t_string,
                        new_add_for_no_add,
                        {}
                        )
                        
                    ref = hyp_indexer.get_idx(no_add_used_hyp)
                    
                    hyp_redirect = make_hyp_of_correct_type_no_add(
                            (mkref(ref),),
                            self.features
                        )
                        
                    list_first.append(hyp_redirect)
            
            return list_first
                
re_ref = re.compile(r"^\[X(\d+)\]$")

    
class Hypothesis(object):
    def __init__(self, score, parent_bond_rel, features, t_string, dpnd, additionals, initial = False, check = True):
          self.t_string = tuple(t_string)
          self.additionals = additionals
          self.parent_bond_rel = parent_bond_rel
          self.score = score
          self.features = features
          self.dpnd = tuple(dpnd)
          self.initial = initial
          if check:
            #print self
            self.check_consistency()
        
    def convert_to_ken_format(self, convert_pos):
        res = []
        for word in self.t_string:
            m = re_ref.match(word)
            if m:
                ref_id = convert_pos(int(m.groups()[0]))
                res.append("[%i]"%ref_id)
            else:
                res.append(word)
        assert len(self.additionals.lst) == 0
        # list_to_insert = []
        # for additional in hyp.additionals.lst:
            # insertion_pos = (additional.prelist + additional.postlist)[0]
            # num = convert_pos(additional.cnum)
            # list_to_insert.append((insertion_pos, "[%i]"%num))
        # list_to_insert.sort(reverse = True)
        # for insertion_pos, add_ref in list_to_insert:
            # res[insertion_pos:insertion_pos] = [add_ref]
        res.append("|||")
        for name, val in self.features.iteritems():
            res.append("%s=%f"%(name, val))
        return " ".join(res)

    
    def split_node(self, pos, hyp_indexer):
        #print "splitting", self, "at", pos
        self.check_consistency()
        start, end = find_span(pos, self.dpnd)
        new_t_string_inner = self.t_string[start:end]
        
        new_additionals_outer = AdditionalsList()
        new_additionals_inner = AdditionalsList()
        
        for add in self.additionals:
            if start <= add.dpnd < end:
                new_additionals_inner.push(add)
            else:
                new_additionals_outer.push(add)
                
        new_additionals_outer.shift_by_if_higher(start-end+1, start)
        new_additionals_inner.shift_by_if_higher(-start, -1)
        
        new_pb_outer = self.parent_bond_rel
        new_pb_inner = "E" if pos < self.dpnd[pos] else "O"
        
        new_score_outer = self.score
        new_score_inner = 0
        
        new_features_outer = self.features
        new_features_inner = {}
        
        new_dpnd_outer = shift_by_if_higher(self.dpnd[:start] + (self.dpnd[pos],)+self.dpnd[end:], start-end+1, start)
        new_dpnd_inner = shift_or_replace_by_minus1(self.dpnd[start:end], (-start), self.dpnd[pos])
        
        
        # found_root = False
        # for i, pos in enumerate(new_dpnd_inner):
            # if pos<0:
                # assert(not found_root)
                # found_root = True
                # new_dpnd_inner[i] = -1
        assert(sum( (pos_o<0) for pos_o in new_dpnd_outer) == 1), "%r %r %i-%i %i->%i"%(self.dpnd, new_dpnd_outer, start, end, pos, self.dpnd[pos])
        assert(sum( (pos_o<0) for pos_o in new_dpnd_inner) == 1), "dpnd:%r %r %r %i-%i %i->%i"%(self.dpnd, new_dpnd_inner, self.dpnd[start:end], start, end, pos, self.dpnd[pos])
        

        
        inner_hyp = Hypothesis(new_score_inner, new_pb_inner, new_features_inner, new_t_string_inner, new_dpnd_inner, new_additionals_inner)
        
        ref_num = hyp_indexer.get_idx(inner_hyp)
        new_t_string_outer = self.t_string[:start] + ("[X%i]"%ref_num,) + self.t_string[end:]
                
        outer_hyp = Hypothesis(new_score_outer, new_pb_outer, new_features_outer, new_t_string_outer, new_dpnd_outer, new_additionals_outer)
        
        return outer_hyp, inner_hyp, ref_num
        
    def split(self, hyp_indexer):
        
        # split_pos = set()
        # for add in self.additionals.lst:
            # split_pos.add(add.dpnd)
        # ordered_pos = order_pos_by_depth(split_pos, self.dpnd)
        
        outer_hyp = self
        inner_hyp_list = []
        
        #print "start split", self
        
        while 1:
            split_pos = set()
            root = outer_hyp.dpnd.index(-1)
            for add in outer_hyp.additionals.lst:
                if add.dpnd != root:
                    split_pos.add(add.dpnd)
            for pos, word in enumerate(outer_hyp.t_string):
                if outer_hyp.dpnd[pos] != -1 and word.endswith("*") and not outer_hyp.t_string[outer_hyp.dpnd[pos]].endswith("*") and outer_hyp.dpnd[pos] != root:
                    split_pos.add(outer_hyp.dpnd[pos])
            if len(split_pos) == 0:
                break
            ordered_pos = order_pos_by_depth(split_pos, outer_hyp.dpnd)
            pos = ordered_pos[0]
        
            outer_hyp, inner_hyp, ref_num = outer_hyp.split_node(pos, hyp_indexer)
            inner_hyp_list.append((ref_num, inner_hyp))
        return outer_hyp, inner_hyp_list
    
    def demux_all(self, get_special_pre_post_ref, max_depth = 3, depth = 0):
        if len(self.additionals.lst) == 0:
            for hyp in self.demux_optional_words(limit = 256):
                yield hyp
        else:
            for hyp in self.demux_first_additional(get_special_pre_post_ref):
                for hyp2 in hyp.demux_all(get_special_pre_post_ref, depth = depth + 1):
                    yield hyp2
                    if depth >= max_depth: #if max depth, only return the first one
                        break
    
    def demux_first_additional(self, get_special_pre_post_ref):
        #print "demuxing first add of", self
        res = []
        assert(len(self.additionals.lst) > 0 )
        add = self.additionals.lst[0]
        cnum = add.cnum
        
        pre_ref_num = get_special_pre_post_ref(cnum, "E")
        if pre_ref_num is not None:
            hyp_pre = Hypothesis(0, "E", {}, ("[X%i]"%pre_ref_num,), (-1,), AdditionalsList())
            for hyp in self.combine_with_inner(hyp_pre, cnum):
                yield hyp
            
        
        post_ref_num = get_special_pre_post_ref(cnum, "O")
        if post_ref_num is not None:
            hyp_post = Hypothesis(0, "O", {}, ("[X%i]"%post_ref_num,), (-1,), AdditionalsList())
            for hyp in self.combine_with_inner(hyp_post, cnum):
                yield hyp
          
    def demux_optional_words(self, limit = 1000):
        assert(len(self.additionals.lst) == 0)
        res = []
        option_pos_list = []
        for pos, word in enumerate(self.t_string):
            if word.endswith("*"):
                option_pos_list.append(pos)
        # if len(option_pos_list) < 10:
            # for comb in xrange(2**10):
                
        from itertools import combinations, chain
        n = len(option_pos_list)
        option_pos_list_as_set = set(option_pos_list)
        for num_subset, subset in enumerate(chain(*[combinations(range(n), ni) for ni in range(n+1)])):
            if num_subset > limit:
                return
            subset_as_set = set(option_pos_list[i] for i in subset)
            assert(len(subset_as_set) == len(subset)), "%r != %r"%(subset_as_set, subset)
            new_t_string = []
            new_dpnd = []
            for pos, word in enumerate(self.t_string):
                if pos in option_pos_list_as_set:
                    assert(word.endswith("*"))
                    #assert(self.dpnd[pos] != -1), "%s"%self
                    if pos in subset_as_set:
                        new_t_string.append(word[:-1])
                        new_dpnd.append(self.dpnd[pos])
                else:
                    new_t_string.append(word)
                    new_dpnd.append(self.dpnd[pos])
            yield Hypothesis(self.score, self.parent_bond_rel, self.features, tuple(new_t_string), new_dpnd, self.additionals, self.initial, check = False)
                
    def __str__(self):
        return "%s<%f|%r|%r|%s|%s>"%("HI" if self.initial else "H", self.score, self.t_string, self.dpnd, self.parent_bond_rel, self.additionals)
    
    def get_list_of_ref(self):
        reflist = []
        for w in self.t_string:
            if w.startswith("[X") and w.endswith("]"):
                refnum = int(w[2:-1])
                reflist.append(refnum)
        return reflist
    
    def get_full_list_of_outer(self):
        return self.get_list_of_ref() + [add.cnum for add in self.additionals.lst]
    
    def check_consistency(self):
        assert len(self.dpnd) == len(self.t_string), "%r  %r"%(self.dpnd, self.t_string)
        assert -1 in self.dpnd, "dpnd: %r"%(self.dpnd,)
        assert all(pos!=parent for pos,parent in enumerate(self.dpnd)),"%s"%self
        assert sum( (pos < 0) for pos in self.dpnd) == 1, "dpnd: %r"%(self.dpnd,)
        assert len(set(add.cnum for add in self.additionals.lst)) == len(list(add.cnum for add in self.additionals.lst))
        assert len(set(add.cnum for add in self.additionals.lst) & set(self.get_list_of_ref())) == 0
        #print self
        assert len(set(self.get_list_of_ref())) == len(self.get_list_of_ref()), "%r"%self.get_list_of_ref()
        assert self.features is not None
        self.additionals.check_consistency(self.dpnd)
    
    def __eq__(self, other):
        return (self.t_string == other.t_string and self.additionals == other.additionals and self.parent_bond_rel == other.parent_bond_rel and self.dpnd ==other.dpnd
                    and self.features == other.features)
                    
    def __hash__(self):
        return hash((self.t_string, self.additionals, self.parent_bond_rel, self.dpnd, frozenset(self.features.iteritems())))
    
    def score_with_weights(self, weights):
        score = 0
        for name, val in self.features.iteritems():
            assert name in weights
            score += val * weights[name]
        self.score = score
    
    def combine_with_inner(self, inner, input_pos_of_inner):
        new_parent_bond_rel =self.parent_bond_rel
        new_score = self.score + inner.score
        new_features = merge_features(self.features, inner.features)
        
        
        ref_repr = "[X%i]"%input_pos_of_inner
        if ref_repr in self.t_string:
            pos_in_t_string = self.t_string.index(ref_repr)
            
            if pos_in_t_string in self.dpnd:
                assert(False)
                
            new_t_string, new_dpnd, new_additionals = make_merged(
                    self.t_string, inner.t_string, self.dpnd, inner.dpnd,self.additionals, 
                    inner.additionals ,pos_in_t_string, mode = "replace")
            
            yield Hypothesis(new_score, new_parent_bond_rel, new_features, new_t_string, new_dpnd, new_additionals)
                
        else:
            additionals = self.additionals.copy()
            additional = additionals.pop(input_pos_of_inner)
            if inner.parent_bond_rel == "E" or inner.parent_bond_rel == "U":
                insertion_pos_list = additional.prelist
            elif inner.parent_bond_rel == "O":
                insertion_pos_list = additional.postlist
            else:
                assert(False)
            for insertion_pos in insertion_pos_list:
                new_t_string, new_dpnd, new_additionals = make_merged(
                        self.t_string, inner.t_string, self.dpnd, inner.dpnd, additionals, 
                        inner.additionals, insertion_pos, mode = "insertion", dpnd_point = additional.dpnd)
                yield Hypothesis(new_score, new_parent_bond_rel, new_features, new_t_string, new_dpnd, new_additionals)   


def merge_features(f1, f2):
    res = dict(f1)
    for key,val in f2.iteritems():
        if key in res:
            res[key] += val
        else:
            res[key] = val
    return res          
 
def shift_by(lst, offset):
    type_of_seq = type(lst)
    return type_of_seq((i+offset) for i in lst)

def shift_by_if_not_minus1(lst, offset):
    type_of_seq = type(lst)
    return type_of_seq(((i+offset) if i != -1 else -1) for i in lst)
 
def shift_by_if_higher(lst, offset, threshold):
    type_of_seq = type(lst)
    return type_of_seq((i if i<=threshold else i+offset) for i in lst)
    
def shift_or_replace_minus1(lst, offset, replacement):
    type_of_seq = type(lst)
    return type_of_seq((i+offset if i != -1 else replacement) for i in lst)

def shift_or_replace_by_minus1(lst, offset, replacement):
    type_of_seq = type(lst)
    return type_of_seq((i+offset if i != replacement else -1) for i in lst)
 
    
def make_merged(outer_t_string, inner_t_string, outer_dpnd, inner_dpnd, outer_additionals, inner_additionals ,modification_point, mode = "replace", dpnd_point = None):
    assert mode in ["replace", "insertion"]
    
    modification_point_end = modification_point+ (1 if mode == "replace" else 0)
    
    size_offset = len(inner_t_string) - (1 if mode == "replace" else 0)
    
    new_t_string = list(outer_t_string)
    new_t_string[modification_point:modification_point_end] = inner_t_string
    
    new_dpnd = list(shift_by_if_higher(outer_dpnd, size_offset, modification_point-1))
    parent_of_inner = outer_dpnd[modification_point] if mode == "replace" else dpnd_point
    if parent_of_inner>=modification_point:
        parent_of_inner += size_offset
    inner_dpnd_shifted = shift_or_replace_minus1(inner_dpnd, modification_point, parent_of_inner)   
    new_dpnd[modification_point:modification_point_end] = inner_dpnd_shifted
    
    new_additionals = outer_additionals.copy()
    if mode == "replace":
        new_additionals.update_after_replacement_at(modification_point, size_offset)
    else:
        new_additionals.update_after_insertion_at(modification_point, dpnd_point, size_offset)

    inner_additionals_modif = inner_additionals.copy()
    inner_additionals_modif.shift_by_if_higher(modification_point, -1)
    new_additionals.lst += inner_additionals.lst
    
    inner_cnum_set = set(inner.cnum for inner in inner_additionals)
    
    def consistency_check():
        for add in new_additionals:
            if add.cnum in inner_cnum_set:
                for pos in add.prelist + add.postlist:
                    if not (modification_point <= pos <= modification_point+size_offset):
                        return False
        return True
    assert(consistency_check())
    
    return new_t_string, new_dpnd, new_additionals
                
    
def test_destruct_hyp():
    add1 = DestructuredAdditional(8, [0,1,2,3,4], [5,6])
    add2 = DestructuredAdditional(9, [0,1,2,3,4], [5,6])
    add3 = DestructuredAdditional(10, [0,1,2,3,4], [5,6])
    add4 = DestructuredAdditional(11, [0,1,2,3,4], [5,6])
    add5 = DestructuredAdditional(12, [0,1,2,3,4], [5,6])
    add6 = DestructuredAdditional(13, [0,1,2,3,4], [5,6])
    add7 = DestructuredAdditional(14, [0,1,2,3,4], [5,6])
    add8 = DestructuredAdditional(15, [0,1,2,3,4], [5,6])
    size_input = 20
    def get_special_pre_post_ref(root, parent_bond_rel):
        if parent_bond_rel == "E" or parent_bond_rel == "U":
            return size_input+2+2*root
        if parent_bond_rel == "O":
            return size_input+2+2*root+1
        assert False
        
    def make_original_ref(root):
        return RefType("XO%i"%root)

    def make_original_ref_add(root, parent_bond_rel):
        cnum_mod = get_special_pre_post_ref(root, parent_bond_rel)
        if cnum_mod is None:
            return None
        else:
            return make_original_ref(cnum_mod)

    hyp = DestructuredHypothesis(
            tuple("a* k* [X23] b c d* e f g".split()), 
            DestructuredAdditionalsList([add1,add2, add3, add4, add5, add6, add7, add8]),
            {"f1":4, "f2":5})
    hyp_exp = hyp.split_linear_from_right(make_original_ref_add)
    hyp_exp.remove_empty_production()
    print len(hyp_exp)
    for ref, hyplist in hyp_exp.ref_to_hyp.iteritems():
        print ref, "  ".join(str(hyp) for hyp in hyplist)
    # for num, hyp in enumerate(hyp_exp.developp()):
        # print num, hyp
if __name__ == "__main__":
    test_destruct_hyp()