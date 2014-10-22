import sys,codecs, subprocess, os

if len(sys.argv) != 4:
    print "Usage: python %s rnnlm_bin_path rnnlm_file nbest_file"%sys.argv[0]
    sys.exit(1)
    
rnlm_bin_path, rnnlm_file, nbest_file = sys.argv[1:4]


temp_filename = nbest_file+".rnnlm.temp"
temp = codecs.open(temp_filename, "w", encoding="utf8")

nb_lines = 0
if 1:
    print "Building temporary corpus"
    with codecs.open(nbest_file, encoding="utf8") as nbest:
        for line in nbest:
            splitted_line = line.split("|||")
            assert(len(splitted_line) == 4);
            sentence = splitted_line[1]
            sentence = sentence.strip() + "\n"
            temp.write(sentence)
            nb_lines += 1
            
    print "nbest senteces: ", nb_lines

cmd = "%s -rnnlm %s -test %s -nbest -debug 0"%(rnlm_bin_path, rnnlm_file, temp_filename)
print "Executing: %s"%cmd

p = subprocess.Popen(cmd.split(), stdout = subprocess.PIPE, stderr = sys.stderr)
out, err = p.communicate()
print "done executing"
#print out
#print err
print "removing temp file", temp_filename
os.remove(temp_filename)

score_list = out.split("\n")
assert(len(score_list) == nb_lines + 1), "%i != %i"%(len(score_list) , nb_lines)

temp_nbest_filename = nbest_file+".new.temp"
new_nbest_list = codecs.open(temp_nbest_filename, "w", encoding="utf8")

print "creating new nbest file"
with codecs.open(nbest_file, encoding="utf8") as nbest:
    for num_line, line in enumerate(nbest):
        splitted_line = line.split("|||")
        assert(len(splitted_line) == 4);
        features = splitted_line[2]
        features += score_list[num_line] + " "
        new_line = "|||".join(splitted_line[:2] + [features] + splitted_line[3:])
        new_nbest_list.write(new_line)

os.rename(nbest_file, nbest_file + ".backup")
os.rename(temp_nbest_filename, nbest_file)