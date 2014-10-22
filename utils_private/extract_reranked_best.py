import sys,codecs, subprocess, os

if len(sys.argv) != 3:
    print "Usage: python %s nbest_fn weights_fn"%sys.argv[0]
    sys.exit(1)
    
nbest_fn, weights_fn = sys.argv[1:3]

nbest = codecs.open(nbest_fn, encoding = "utf8")

weights_file = codecs.open(weights_fn, encoding = "utf8")
weights = []
for line in weights_file:
    line = line.strip()
    if line.startswith("#"):
      continue
    splitted_line = line.split()
    assert len(splitted_line) == 2
    weights.append(float(splitted_line[1]))

def compute_score(feat):
    assert len(feat) == len(weights)
    score = 0
    for i in range(len(feat)):
        score += feat[i] * weights[i]
    return score

nb_sentences = 0
best_sentences = {}

for line in nbest:
    splitted_line = line.split("|||")
    assert(len(splitted_line) == 4);
    sentence = splitted_line[1].strip()
    features = splitted_line[2]
    num_line = int(splitted_line[0])
    
    feat_vect = [float(x) for x in features.split() if (len(x) > 0 and x[0]!='r' and x[0]!='f')]
    score = compute_score(feat_vect)
    if num_line not in best_sentences:
        nb_sentences += 1
        best_sentences[num_line] = {"first": sentence, "best": sentence, "best_score":score}
    else:
        if score > best_sentences[num_line]["best_score"]:
            best_sentences[num_line]["best_score"] = score
            best_sentences[num_line]["best"] = sentence
    assert nb_sentences-1 == num_line, "%i != %i"%(nb_sentences, num_line) 
            
assert(len(best_sentences) == nb_sentences)
print nb_sentences, " sentences found"
best_file = codecs.open("best_"+nbest_fn, "w", encoding = "utf8")
first_file = codecs.open("first_" + nbest_fn, "w", encoding="utf8")

for num_sent in range(nb_sentences):
    #print " ".join(best_sentences[num_sent]["best"]+ "\n")
    best_file.write(best_sentences[num_sent]["best"]+ "\n")
    first_file.write(best_sentences[num_sent]["first"] + "\n")
    
    
