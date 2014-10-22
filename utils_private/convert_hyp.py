import logging
from collections import defaultdict
import functools
import re, codecs
import hypothesis
reload(hypothesis)
#from hypothesis import Hypothesis, AugmentedPattern, AdditionalsList, Additional

#logger = logging.getLogger()#"Decoder")

escape_dict = {"0":"", "\\":"\\", "n":"\n", "_":" ", "p":"|"}
def de_escape(string):
    if "\\" not in string:
        return string
    res = []
    cursor = 0
    while(cursor < len(string)):
        c = string[cursor]
        if c!="\\":
            res.append(c)
        else:
            cursor += 1
            c = string[cursor]
            res.append( escape_dict[c])
        cursor += 1
    return "".join(res)

re_multi_ref = re.compile(r"^\[X(\d+\,)+\d+\]$")
    
def parse_hypothesis_file(f):
    starting_hypothesis = {}
    current_pattern = None
    for num_line, line in enumerate(f):
        line = line.strip()
        if num_line == 0:
            assert(line.startswith("START"))
            splitted = line.split()
            assert(len(splitted) == 2)
            assert(splitted[0] == "START")
            size_input = int(splitted[1])
        elif num_line == 1:
            feature_names = line.split()
        elif line.startswith("END"):
            break
        elif line.startswith("P|"):
            fields = line.split("|")
            assert(len(fields) == 6)
            pattern = [int(i) for i in fields[1].split()]
            root = int(fields[2])
            parent = int(fields[3])
            outer = [int(i) for i in fields[4].split()]
            inner = {}
            for inner_as_string in fields[5].split():
                inner_as_string_splitted = inner_as_string.split(":")
                assert(len(inner_as_string_splitted) == 2)
                inner_pos = int(inner_as_string_splitted[0])
                outer_of_inner = [int(i) for i in inner_as_string_splitted[1].split("_")]
                inner[inner_pos] = outer_of_inner
            augmented_pattern = hypothesis.AugmentedPattern(pattern, root, parent, inner, outer)
            current_pattern = augmented_pattern
            starting_hypothesis[current_pattern] = []
        else:
            assert current_pattern is not None
            #print "parsing hyp:", line
            fields = line.split("|")
            assert(len(fields) == 8), "%i!=8 (%s)"%(len(fields), line)
            score = float(fields[0])
            t_string = [de_escape(string) for string in fields[1].split()]
            if any((not not re_multi_ref.match(w)) for w in t_string):
                logging.error("Had to remove hypothesis with multi-ref.")
                continue
            dpnd = [int(i) for i in fields[2].split()]
            parent_bond_rel = fields[3]
            additionals = hypothesis.AdditionalsList()
            for additional_as_string in fields[4] .split():
                additional_fields = additional_as_string.split(":")
                cnum = int(additional_fields[0])
                add_dpnd = int(additional_fields[1])
                prelist = [int(i) for i in additional_fields[2].split("_")]
                postlist = [int(i) for i in additional_fields[3].split("_")]
                additionals.push(hypothesis.Additional(cnum, add_dpnd, prelist, postlist))
            features = {}
            for feature_as_string in fields[7].split():
                feature_as_string_splitted = feature_as_string.split(":")
                features[ feature_names[int(feature_as_string_splitted[0])] ] = float(feature_as_string_splitted[1])
                
            if sum( (ix < 0) for ix in dpnd) != 1:
                logging.error("Had to remove inconsistent hypothesis: more than one -1 in dpnd")
                continue
                
            hyp = hypothesis.Hypothesis(score, parent_bond_rel, features, t_string, dpnd, additionals, initial = True)
            if set(hyp.get_full_list_of_outer()) != set(current_pattern.outer):
                logging.error("Had to remove inconsistent hypothesis: pattern/hyp incompatibility")
                continue
            if len(set(hyp.get_list_of_ref())) != len(hyp.get_list_of_ref()):
                logging.error("Had to remove inconsistent hypothesis: same ref appearing more than once")
                continue

                
            assert set(hyp.get_full_list_of_outer()) == set(current_pattern.outer), "incompatible:%s %s : %r != %r [%i]"%(hyp, current_pattern, hyp.get_full_list_of_outer(), current_pattern.outer, num_line + 1)
            hyp.check_consistency()
            starting_hypothesis[current_pattern].append(hyp)
    return starting_hypothesis, size_input
   

        
     
def get_map_to_topological_order(outer_by_root): #not efficient but should be enough
    # outer_by_root = defaultdict(set)
    # for pattern in starting_hypothesis:
        # outer_by_root[pattern.root] |= set(pattern.outer)
    already_out = set()
    not_yet_out = set(outer_by_root.keys())
    sorted_list = []
    
    while len(not_yet_out) > 0:
        changed = False
        for pos in set(not_yet_out):
            if outer_by_root[pos].issubset(already_out):
                sorted_list.append(pos)
                not_yet_out.remove(pos)
                already_out.add(pos)
                changed = True
        if not changed:
            print outer_by_root
            print
            print already_out
            print not_yet_out
            print 
            assert(changed)
    return dict( (j,i) for i,j in enumerate(sorted_list) )

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
    
def get_map_to_topological_order_better(outer_by_root): 
    res = toposort2(outer_by_root)
    sorted_list = [x for lst in res for x in lst]
    return dict( (j,i) for i,j in enumerate(sorted_list) )
    
class HypIndexer(object):
    def __init__(self, min_index):
        self.hyp_to_index = {}
        self.index_to_hyp = {}
        self.min_index = min_index
        self.max_index = self.min_index-1
    
    def get_hyp(self, idx):
        assert (self.min_index<= idx <= self.max_index)
        return self.index_to_hyp[idx]
        
    def __len__(self):
        return len(self.hyp_to_index)
        
    def get_idx(self, hyp):
        if hyp not in self.hyp_to_index:
            self.max_index+=1
            self.hyp_to_index[hyp] = self.max_index
            self.index_to_hyp[self.max_index] = hyp
        return self.hyp_to_index[hyp]

def identify_real_root(pattern_list): 

    pattern_by_root = defaultdict(set)
    for pat in pattern_list:
        pattern_by_root[pat.root].add(pat)
        
    relation_graph = {}
    for pat in pattern_list:
        relation_graph[pat] = set()
        for root in pat.outer:
            relation_graph[pat]|=pattern_by_root[root]

    res = toposort2(relation_graph)
    sorted_list = [x for lst in res for x in lst]
            
    pat_to_max_cover = {}
    max_cover_to_pat = defaultdict(set)
    longest_length = None
    #print sorted_list
    for pat in sorted_list:
        #print pat
        pat_to_max_cover[pat] = set(pat.pattern)
        for root in pat.outer:
            if root not in pattern_by_root:
                assert root not in pattern_by_root
            for pat2 in pattern_by_root[root]:
                pat_to_max_cover[pat] |= pat_to_max_cover[pat2]
        max_cover = frozenset(pat_to_max_cover[pat])
        max_cover_to_pat[max_cover].add(pat)
        if longest_length is None or len(max_cover) > longest_length:
            longest_length = len(max_cover)
            
    total_cover = frozenset(range(longest_length))
    assert total_cover in max_cover_to_pat
    root_list = [pat.root for pat in max_cover_to_pat[total_cover]]
    assert len(root_list) >= 1
    assert len(set(root_list)) == 1
    return root_list[0]
    
def gen_kenlm(starting_hypothesis, size_input, out):

    def get_special_pre_post_ref(root, parent_bond_rel):
        if parent_bond_rel == "E" or parent_bond_rel == "U":
            return size_input+2+2*root
        if parent_bond_rel == "O":
            return size_input+2+2*root+1
        assert False

    def demux_pre_post_ref(root):
        pre_ref = get_special_pre_post_ref(root, "E")
        post_ref = get_special_pre_post_ref(root, "O")
        return pre_ref, post_ref
        
    real_root = identify_real_root(starting_hypothesis.keys())
        
    hypotheses_by_root = defaultdict(set)
    pattern_base = None
    # tuple_full = tuple(range(size_input))
    for pattern, hypotheses_set in starting_hypothesis.iteritems():
        # if pattern.pattern == tuple_full:
            # assert pattern_base is None
            # pattern_base = pattern
        for hyp in hypotheses_set:
            #hypotheses_by_root[pattern.root].add(hyp)
            modif_root = get_special_pre_post_ref(pattern.root, hyp.parent_bond_rel)
            hypotheses_by_root[modif_root].add(hyp)
            hypotheses_by_root[pattern.root].add(hypothesis.SpecialHypRef(modif_root))
    # assert pattern_base is not None
    
    outer_by_root = defaultdict(set)
    for pattern in starting_hypothesis:  
        for d_root in demux_pre_post_ref(pattern.root):  # to optimize
            if d_root not in hypotheses_by_root:
                continue
            outer_by_root[d_root] |= set(pattern.outer)
            outer_by_root[pattern.root].add(d_root)
                
    hyp_indexer = HypIndexer(256+size_input*3)
    
    split_hypotheses_by_root = defaultdict(set)
    
    for root, hypotheses_set in hypotheses_by_root.iteritems():
        for hyp in hypotheses_set:
            outer, inners = hyp.split(hyp_indexer)
            split_hypotheses_by_root[root].add(outer)
            for ref_num, inner in inners:
                outer_by_root[root].add(ref_num)
    
    for root, hyp in hyp_indexer.index_to_hyp.iteritems() :
        split_hypotheses_by_root[root].add(hyp)
        ref_list = hyp.get_full_list_of_outer()
        outer_by_root[root] |= set(ref_list)
        
    def get_special_pre_post_ref_if_exists(root, parent_bond_rel):
        ref = get_special_pre_post_ref(root, parent_bond_rel)
        if ref in split_hypotheses_by_root:
            return ref
        else:
            return None
        
    gen_ken_format_better(outer_by_root, split_hypotheses_by_root, out, get_special_pre_post_ref_if_exists, real_root)
            
def gen_ken_format_better(relation_graph, hypotheses_by_root, out, get_special_pre_post_ref, real_root):

    hypcomp = hypothesis.HypCompressor()
    map_root_to_new_ref = {}
    def make_original_ref(root):
        return hypothesis.RefType("XO%i"%root)
        
    def make_original_ref_add(root, parent_bond_rel):
        cnum_mod = get_special_pre_post_ref(root, parent_bond_rel)
        if cnum_mod is None:
            return None
        else:
            return make_original_ref(cnum_mod)
           
    re_ref = re.compile(r"^\[X(\d+)\]$")
    def t_string_to_ref_func(w):
        m = re_ref.match(w)
        if not m:
            return w
        else:
            root = int(m.groups()[0])
            return make_original_ref(root)
            
    sorted_list_by_level = toposort2(relation_graph)
    sorted_list = [x for lst in sorted_list_by_level for x in lst]
    print "expansion"
    import gc
    gc.disable()
    for root in sorted_list:
        #print root
        hypotheses_set = hypotheses_by_root[root]
        #print ">>>"
        for num_hyp, hyp in enumerate(hypotheses_set):
            #if (num_hyp+1)%100 == 0:
            #    print num_hyp+1,"/",len(hypotheses_set), hyp
            
            hyp = hypothesis.DestructuredHypothesis.convert_from_hypothesis(hyp, t_string_to_ref_func, make_original_ref)
            assert not hyp.is_empty()
            hyp_exp = hyp.split_linear_from_right(make_original_ref_add)
            hyp_exp.remove_empty_production(remove_unique_ref = True)
            hypcomp.merge(hyp_exp, map_root_to_new_ref)
        new_ref = hypcomp.freeze_and_reset_base_ref()
        map_root_to_new_ref[make_original_ref(root)] = new_ref
        #print root, new_ref
    print "ready to write"
    real_root_ref = make_original_ref(real_root)
    new_real_root_ref = map_root_to_new_ref[real_root_ref]
    #print "map_root_to_new_ref",map_root_to_new_ref
    hypcomp.write_as_ken_format(out, new_real_root_ref)
    gc.enable()
                
def gen_ken_format(relation_graph, hypotheses_by_root, out, get_special_pre_post_ref):

    topo_map = get_map_to_topological_order_better(relation_graph)
    def convert_pos(i):
        return topo_map[i]
    
    edge_by_root = {}
    for root, hypotheses_set in hypotheses_by_root.iteritems():
        print "demuxing root", root
        demuxed_hyp = set()
        for hyp in hypotheses_set:
            print "demuxing hyp", hyp
            for hyp_std in hyp.demux_all(get_special_pre_post_ref):
                demuxed_hyp.add(hyp_std)
        edge_by_root[convert_pos(root)] = demuxed_hyp
        
    total_edge_count = sum(len(demuxed_hyp) for demuxed_hyp in edge_by_root.itervalues())
        
    vertex_list  = sorted(edge_by_root.keys())
    #assert(len(vertex_list) == size_input)
    out.write("%i %i\n"%(len(vertex_list)+1, total_edge_count+1)) #+1 for final rule
    #for num_vertex, vertex in enumerate(vertex_list):
        #assert(num_vertex == vertex)
    for vertex in range(len(topo_map)):
        if vertex not in edge_by_root:
            out.write("0\n")
            continue
        out.write("%i\n"%len(edge_by_root[vertex]))
        for hyp in edge_by_root[vertex]:
            out.write(hyp.convert_to_ken_format(convert_pos))
            out.write("\n")
    out.write("1\n<s> [%i] </s> ||| \n"%(len(topo_map)-1))

def filter_hyp(starting_hypothesis):
    res = defaultdict(list)
    
    for pat in starting_hypothesis:
        already_found = set()
        for hyp in starting_hypothesis[pat]:
            if hyp in already_found:
                continue
            if len("".join(hyp.t_string).strip()) == 0:
                hyp.t_string = ("$#00#$",)
            res[pat].append(hyp)
            already_found.add(hyp)
    return res

def test1():
    minihyp = """START 1
NULL_content NULL_function abnormal_child_bond both_ROS child_bond_count child_bond_similarity different_parent_cat example_penalty lm no_redundant_child numeral_mismatch one_side_ROS parent_bond_LD parent_bond_available parent_bond_similarity redundant_child_in_input redundant_child_in_source root_LD same_parent_cat same_root_content size trans_lm_prob trans_prob trans_prob_multiplied_by_size tree_lm zbond_exact zbond_partial
P|0|0|1||
0|this process|1 -1|O||NN||7:1 9:1 18:1 19:1 21:1 22:0.058823529411764705 23:0.058823529411764705
0|such means|1 -1|O||NNS||7:1 9:1 18:1 19:1 21:1 22:0.019607843137254902 23:0.019607843137254902
0|this|-1|E||DT||7:1 9:1 13:1 19:1 21:0.98039215686274506 22:1 23:1
END
""".split("\n")
    starting_hypothesis, size_input = parse_hypothesis_file(minihyp)
    import sys
    gen_kenlm(starting_hypothesis, size_input, sys.stdout)
        
   
def test_split():
    minihyp = """START 18
NULL_content NULL_function abnormal_child_bond both_ROS child_bond_count child_bond_similarity different_parent_cat example_penalty lm no_redundant_child numeral_mismatch one_side_ROS parent_bond_LD parent_bond_available parent_bond_similarity redundant_child_in_input redundant_child_in_source root_LD same_parent_cat same_root_content size trans_lm_prob trans_prob trans_prob_multiplied_by_size tree_lm zbond_exact zbond_partial
P|3 4 9 10 11 12 13 14 15 16|14|-1|2 8 17|3:2 9:8 14:17
0|and* 110120 are controlled individually based on an* output signal|1 3 3 -1 3 3 5 9 9 6|U|2:1:0_1:2:CD 8:8:8:9:NN 17:3:0_2_3:4_5_10:VBN|VBN||1:2 3:1 7:1 10:1 15:3 16:5 17:-0.29999999999999999 19:1 20:9 21:1 22:0.5 23:5
0|the* [X2] 110120 are controlled by output signals|2 2 4 4 -1 4 7 5|U|8:6:6:7:NN 17:4:0_3_4:5_8:VBN|VBN|1:NN|0:1 1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:0.5 22:1 23:10
0|and the* [X2] 110120 are controlled by output signals|5 3 3 5 5 -1 5 8 6|U|8:7:7:8:NN 17:5:0_1_4_5:6_9:VBN|VBN|2:JJ|1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:1 22:0.5 23:5
END
""".split("\n")
    starting_hypothesis, size_input = parse_hypothesis_file(minihyp)
    starting_hypothesis = filter_hyp(starting_hypothesis)
    print starting_hypothesis
    hyplist = starting_hypothesis.values()[0]
    
    hyp_indexer = HypIndexer(256)
    for hyp in hyplist:
        print hyp
        outer, inners= hyp.split(hyp_indexer)
        print outer
        for inner in inners:
            print inner
        print
# 0|the* [X2] 110120 are controlled by output signals|2 2 4 4 -1 4 7 5|U|8:6:6:7:NN 17:4:0_3_4:5_8:VBN|VBN|1:NN|0:1 1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:0.5 22:1 23:10
# 0|and the* [X2] 110120 are controlled by output signals|5 3 3 5 5 -1 5 8 6|U|8:7:7:8:NN 17:5:0_1_4_5:6_9:VBN|VBN|2:JJ|1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:1 22:0.5 23:5
def test_split_refactor():
    minihyp = """START 18
NULL_content NULL_function abnormal_child_bond both_ROS child_bond_count child_bond_similarity different_parent_cat example_penalty lm no_redundant_child numeral_mismatch one_side_ROS parent_bond_LD parent_bond_available parent_bond_similarity redundant_child_in_input redundant_child_in_source root_LD same_parent_cat same_root_content size trans_lm_prob trans_prob trans_prob_multiplied_by_size tree_lm zbond_exact zbond_partial
P|1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17|14|-1||
0|TT TT is* 110120 TT TT TT TT are controlled individually based on an* output signal TT TT|1 3 3 -1 3 3 5 9 9 6 3 3 3 3 3 3 3 3|U||VBN||1:2
P|3 4 9 10 11 12 13 14 15 16|14|-1|2 8 17|3:2 9:8 14:17
0|and* 110120 are controlled individually based on an* output signal|1 3 3 -1 3 3 5 9 9 6|U|2:1:0_1:2:CD 8:8:8:9:NN 17:3:0_2_3:4_5_10:VBN|VBN||1:2 3:1 7:1 10:1 15:3 16:5 17:-0.29999999999999999 19:1 20:9 21:1 22:0.5 23:5
0|the* [X2] 110120 are controlled by output signals|2 2 4 4 -1 4 7 5|U|8:6:6:7:NN 17:4:0_3_4:5_8:VBN|VBN|1:NN|0:1 1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:0.5 22:1 23:10
0|and the* [X2] 110120 are controlled by output signals|5 3 3 5 5 -1 5 8 6|U|8:7:7:8:NN 17:5:0_1_4_5:6_9:VBN|VBN|2:JJ|1:2 3:1 4:1 7:1 10:1 15:2 16:4 17:-0.29999999999999999 19:1 20:9 21:1 22:0.5 23:5
P|0 1 2|2|3||
0|HHHH HHHH OOOO|1 2 -1|E||VBN||
P|5 6 7 8|8|9||
0|LLL LLL LLL LLL|1 2 3 -1|O||VBN||
0|LLL MMMM JJJ LLL|1 2 3 -1|O||VBN||
P|17|17|14||
0|NNNN|-1|E||VBN||
END
""".split("\n")
    starting_hypothesis, size_input = parse_hypothesis_file(minihyp)
    starting_hypothesis = filter_hyp(starting_hypothesis)
    print starting_hypothesis
    
    import sys
    gen_kenlm(starting_hypothesis, size_input, sys.stdout)
    
        
def cmd():
    import sys
    hyp_file = sys.argv[1]
    f = codecs.open(hyp_file, encoding = "utf8")
    
    out_file = sys.argv[2]
    out = codecs.open(out_file, "w", encoding = "utf8")
    starting_hypothesis, size_input = parse_hypothesis_file(f)
    print "loaded"
    starting_hypothesis = filter_hyp(starting_hypothesis)
    print "filtered"
    gen_kenlm(starting_hypothesis, size_input, out)
    print "done"
    
    
if __name__ == "__main__":
    cmd()
    #import cProfile
    #cProfile.run("cmd()")
    #test_split()
    #test_split_refactor()
    
