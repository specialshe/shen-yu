#!/usr/bin/env perl

use strict;
use XML::Simple;
use Scalar::Util;
use Getopt::Long;
use utf8;

binmode STDIN, ":encoding(utf8)";
binmode STDOUT, ":encoding(utf8)";

my $opt = {output_mode => 'html'};
GetOptions($opt, 'help', 'output_mode=s');

if ($opt->{help}) {
    &print_help();
}

my $TableDisplay;
if ($opt->{output_mode} eq 'html') {
    eval {require TableDisplay};
    if ($@) {
        &print_help();
    }
    $TableDisplay = new TableDisplay({encoding => 'utf8'});
}

unless ($ENV{"XML_SIMPLE_PREFERRED_PARSER"}) {
    $ENV{"XML_SIMPLE_PREFERRED_PARSER"} = "XML::Parser";
}
my $xml = new XML::Simple;

sub main {
    my $fh = \*STDIN;
    if ($ARGV[0]) {
        open($fh, "<:encoding(utf8)", $ARGV[0]) || die;
    } else {
        &print_help();
    }
    while (my $DTREE = &get_one_sentence($fh)) {
        my $result = &print_web_matrix($DTREE);
        if ($opt->{output_mode} eq 'html') {
            open(OUT, ">:encoding(utf8)", $DTREE->{id}.".html") || die;
            print OUT $TableDisplay->convert($result);
            close OUT;
        } else {
            open(OUT, ">:encoding(utf8)", $DTREE->{id}.".txt") || die;
            print OUT $result;
            close OUT;
        }
    }
}

sub get_one_sentence {
    my ($fh) = @_;

    while (1) {
        my $tag_prefix = "";
        my $flag = 0;
        my $buf = "";
        # 対訳文を一つ読み込む
        while (readline($fh)) {
            if (/\s*\<(para_|)sentence id=\"(.+?)\"/) {
                $tag_prefix = $1;
                my $id = $2;
                $buf .= $_;
                $flag = 1;
            } elsif (/\s*\<\/($tag_prefix)sentence/) {
                $buf .= $_;
                $flag = 0;
                last;
            } elsif ($flag) {
                $buf .= $_;
            }
        }
        next if ($flag);
        last if ($buf eq "");

        my $DTREE;
        eval {$DTREE = $xml->XMLin($buf, ForceArray => 1, keyattr => [])};
        if ($@) {
            print STDERR "$@\n";
            $flag = 0;
            next;
        }
        if (!defined $DTREE->{i_data} ||
            !defined $DTREE->{j_data} ||
            ref($DTREE->{i_data}[0]) ne 'HASH' ||
            ref($DTREE->{j_data}[0]) ne 'HASH' ||
            !defined $DTREE->{i_data}[0]{phrase} ||
            !defined $DTREE->{j_data}[0]{phrase}) {
            print STDERR "$DTREE->{id}: Illegal sentence structure\n";
            next;
        }

        @{$DTREE->{i_data}} = sort {$b->{prob} <=> $a->{prob}} @{$DTREE->{i_data}};
        @{$DTREE->{j_data}} = sort {$b->{prob} <=> $a->{prob}} @{$DTREE->{j_data}};
        for (my $i = $#{$DTREE->{i_data}}; $i >= 0; $i--) {
            # dpnd_check
            my $root_count = 0;
            for (my $p = 0; $p < @{$DTREE->{i_data}[$i]{phrase}}; $p++) {
                $root_count++ if ($DTREE->{i_data}[$i]{phrase}[$p]{dpnd} == -1);
            }
            if ($root_count != 1) {
                print STDERR "i ROOT NUM ERROR!\n";
                splice(@{$DTREE->{i_data}}, $i, 1);
                next;
            }
            &format_dtree($DTREE->{i_data}[$i]);
        }

        for (my $j = $#{$DTREE->{j_data}}; $j >= 0; $j--) {
            # dpnd_check
            my $root_count = 0;
            for (my $p = 0; $p < @{$DTREE->{j_data}[$j]{phrase}}; $p++) {
                $root_count++ if ($DTREE->{j_data}[$j]{phrase}[$p]{dpnd} == -1);
            }
            if ($root_count != 1) {
                print STDERR "j ROOT NUM ERROR!\n";
                splice(@{$DTREE->{j_data}}, $j, 1);
                next;
            }
            &format_dtree($DTREE->{j_data}[$j]);
        }

        if (scalar(@{$DTREE->{i_data}}) == 0 ||
            scalar(@{$DTREE->{j_data}}) == 0) {
            print STDERR "$DTREE->{id}: No data\n";
            next;
        }

        if (grep($_->{word}[0]{lem} eq "" && $_->{word}[0]{content} eq "", @{$DTREE->{i_data}[0]{phrase}}, @{$DTREE->{j_data}[0]{phrase}})) {
            print STDERR "$DTREE->{id}: Empty Word\n";
            next;
        }

        # match
        if (defined $DTREE->{match}) {
            for (my $i = 0; $i < @{$DTREE->{match}}; $i++) {
                my $m = $DTREE->{match}[$i];
                @{$m->{i_phrases}} = map($DTREE->{i_data}[0]{phrase}[$_], split(" ", $m->{i_p}));
                @{$m->{j_phrases}} = map($DTREE->{j_data}[0]{phrase}[$_], split(" ", $m->{j_p}));
                $m->{i_p_add} = [split(" ", $m->{i_p_add})] if (defined $m->{i_p_add});
                $m->{j_p_add} = [split(" ", $m->{j_p_add})] if (defined $m->{j_p_add});
                foreach my $pnum (split(" ", $m->{i_p})) {
                    $DTREE->{i_data}[0]{phrase}[$pnum]{match} = $i;
                }
                foreach my $pnum (split(" ", $m->{j_p})) {
                    $DTREE->{j_data}[0]{phrase}[$pnum]{match} = $i;
                }
                foreach my $word (@{$m->{word}}) {
                    push(@{$m->{words}}, {i => [map($DTREE->{i_data}[0]{words}[$_], split(/ /, $word->{i_w}))], j => [map($DTREE->{j_data}[0]{words}[$_], split(/ /, $word->{j_w}))]});
                }
                foreach my $deriv (@{$m->{i_deriv}}) {
                    push(@{$m->{i_derivs}}, [split(/ /, $deriv->{pnum})]);
                }
                foreach my $deriv (@{$m->{j_deriv}}) {
                    push(@{$m->{j_derivs}}, [split(/ /, $deriv->{pnum})]);
                }
            }
        }
        return $DTREE;
    }
    return undef;
}

sub format_dtree {
    my ($dtree) = @_;
    my $wc = 0;

    for my $p (@{$dtree->{phrase}}) {
        $p->{pre_children} = [];
        $p->{pre_children_ref} = [];
        $p->{post_children} = [];
        $p->{post_children_ref} = [];
    }

    for (my $i = 0; $i < @{$dtree->{phrase}}; $i++) {
        my $p = $dtree->{phrase}[$i];
        $p->{pnum} = $i;
        if ($p->{dpnd} == -1) {
            $p->{dpnd_ref} = undef;
            $dtree->{root} = $i;
            $dtree->{root_ref} = $p;
        } else {
            my $head = $dtree->{phrase}[$p->{dpnd}];
            $p->{dpnd_ref} = $head;
            Scalar::Util::weaken($p->{dpnd_ref});
            if ($i < $p->{dpnd}) {
                push(@{$head->{pre_children}}, $i);
                push(@{$head->{pre_children_ref}}, $p);
            } else {
                push(@{$head->{post_children}}, $i);
                push(@{$head->{post_children_ref}}, $p);
            }
        }

        for (my $w_num = $#{$p->{word}}; $w_num >= 0; $w_num--) {
            $p->{word}[$w_num]{pnum} = $i;
        }
    }
}

######################################################################
sub print_parallel_dtree {
    my ($fh, $i_root_ref, $j_root_ref, $ast) = @_;

    my @i_tree_buffer;
    &print_dtree($fh, $i_root_ref, "", \@i_tree_buffer, $ast);
    my @j_tree_buffer;
    &print_dtree($fh, $j_root_ref, "", \@j_tree_buffer, $ast);

    my ($max_i_length, @dummy) = sort {$b <=> $a} map(&wlength($_), @i_tree_buffer);
    my ($max_j_length, @dummy) = sort {$b <=> $a} map(&wlength($_), @j_tree_buffer);

    print $fh '-' x ($max_i_length + $max_j_length + 4);
    print $fh "\n";
    for (my $i = 0; $i < @i_tree_buffer || $i < @j_tree_buffer; $i++) {
        print $fh $i_tree_buffer[$i];
        print $fh ' ' x ($max_i_length + 4 - &wlength($i_tree_buffer[$i]));
        print $fh $j_tree_buffer[$i],"\n";
    }
    print $fh "\n";
}

sub print_dtree {
    my ($fh, $phrase_ref, $mark, $b_ref, $ast) = @_;
    my $local_buffer;
    my @children;

    # 前の子の表示
    # print pre-children
    foreach my $c (@{$phrase_ref->{pre_children_ref}}) {
        if ($ast == 1) {
            push(@children, $c) if ($c->{bond} == 0);
        } else {
            push(@children, $c) unless ($c->{bond} == -1);
        }
    }
    if (@children) {
        &print_dtree($fh, shift(@children), $mark . "L", $b_ref, $ast);
        foreach my $c (@children) {
            &print_dtree($fh, $c, $mark . "l", $b_ref, $ast);
        }
    }

    # 自分の表示
    # print self
    my @mark = split("", $mark);
    for (my $m = 0; $m < @mark; $m++) {
        if ($m == $#mark) {
            if ($mark[$m] eq "L") {
                $local_buffer .= '┌';
            } elsif ($mark[$m] eq "R") {
                $local_buffer .= '└';
            } else {
                $local_buffer .= '├';
            }
        } else {
            if ($mark[$m] eq "l" ||
                $mark[$m] eq "r" ||
                ($mark[$m] eq "L" && ($mark[$m+1] eq "r" || $mark[$m+1] eq "R")) ||
                ($mark[$m] eq "R" && ($mark[$m+1] eq "l" || $mark[$m+1] eq "L"))) {
                $local_buffer .= '│';
            } else {
                $local_buffer .= '　';
            }
        }
    }

    $local_buffer .= "( " if (defined $phrase_ref->{lm_check} && defined $phrase_ref->{lm_check} == 1);

    if (defined $phrase_ref->{match}) {
        $local_buffer .= "[$phrase_ref->{match}] ";
    }
    $local_buffer .= &p_string($phrase_ref);

    $local_buffer .= " )" if (defined $phrase_ref->{lm_check} && defined $phrase_ref->{lm_check} == 1);

    if (defined $b_ref) {
        my $p_num = $#{$b_ref} + 1;
        if ($p_num < 10) {
            $p_num = "$p_num ";
        }
        push(@{$b_ref}, "$p_num $local_buffer");
    } else {
        print $fh $local_buffer,"\n";
    }

    # 後ろの子の表示
    # print post-children
    @children = ();
    foreach my $c (@{$phrase_ref->{post_children_ref}}) {
        if ($ast == 1) {
            push(@children, $c) if ($c->{bond} == 0);
        } else {
            push(@children, $c) unless ($c->{bond} == -1);
        }
    }
    if (@children) {
        my $last_child = pop(@children);
        foreach my $c (@children) {
            &print_dtree($fh, $c, $mark . "r", $b_ref, $ast);
        }
        &print_dtree($fh, $last_child, $mark . "R", $b_ref, $ast);
    }
}

# count wide characters as 2 byte
sub wlength {
    my ($string) = @_;
    return length($string) +
        ($string =~ s/[\p{Han}\p{Hiragana}\p{Katakana}・ー．。，、「」├┌└│─　★０-９Ａ-Ｚａ-ｚ＃（）％‐／〜]//g);
}

sub p_string {
    my ($p_ref) = @_;
    my $word_sep = " ";         # always blank char
    my $string = "";

    for my $w (@{$p_ref->{word}}) {
        $string .= $word_sep . $w->{content};
    }
    $string =~ s/^\s//;
    return $string;
}
######################################################################
sub escape_char {
    my ($str) = @_;
    $str =~ s/\&/\&amp\;/g;
    $str =~ s/ /\&nbsp\;/g;
    $str =~ s/　/\&nbsp\;\&nbsp\;/g;
    $str =~ s/\</\&lt\;/g;
    $str =~ s/\>/\&gt\;/g;
    $str =~ s/\"/\&quot\;/g;
    return $str;
}

sub print_web_matrix {
    my ($dtree) = @_;

    my $result;

    my @i_tree_buffer;
    &print_dtree(undef, $dtree->{i_data}[0]{root_ref}, "", \@i_tree_buffer);
    my @j_tree_buffer;
    &print_dtree(undef, $dtree->{j_data}[0]{root_ref}, "", \@j_tree_buffer);

    # source木の描画
    for (my $i = 0; $i < @i_tree_buffer; $i++) {
        $result .= sprintf("%%%% 2 %d %d valign=top\n", $#j_tree_buffer + 2, $i + 2);
        my $tmpstr;
        my $flag = 0;
        $i_tree_buffer[$i] =~ s/^\d  //;
        $i_tree_buffer[$i] =~ s/^\d+ //;
        $i_tree_buffer[$i] =~ s/\[\d+\] //;
        foreach my $str (split ("", $i_tree_buffer[$i])) {
            next if ($str eq " ");
            if ($str eq "│") {
                $str = "─";
            } elsif ($str eq "─") {
                $str = "│";
            } elsif ($str eq "├") {
                $str = "┬";
            } elsif ($str eq "└") {
                $str = "┐";
            }
            $str = &escape_char($str);
            $tmpstr .= "<BR>$str";
        }
        $tmpstr =~ s/^<BR>//;
        $result .= "$tmpstr\n";
    }

    # target木の描画
    for (my $j = 0; $j < @j_tree_buffer; $j++) {
        $result .= sprintf ("%%%% 2 %d %d\n", $j + 1, 1);
        $j_tree_buffer[$j] =~ s/^\d  //;
        $j_tree_buffer[$j] =~ s/^\d+ //;
        $j_tree_buffer[$j] =~ s/\[\d+\] //;
        $j_tree_buffer[$j] = &escape_char($j_tree_buffer[$j]);
        $result .= "$j_tree_buffer[$j]\n";
    }

    $result .= sprintf ("%%%% 2 %d %d extern=show_parse.cgi?id=%s\n", $#j_tree_buffer + 2, 1, $dtree->{id});

    # matrix
    my $matrix;
    if (defined $dtree->{match}) {
        foreach my $match (@{$dtree->{match}}) {
            my @i_derivs;
            foreach my $deriv (@{$match->{i_derivs}}) {
                push(@i_derivs, map($dtree->{i_data}[0]{phrase}[$_], @$deriv));
            }
            my @j_derivs;
            foreach my $deriv (@{$match->{j_derivs}}) {
                push(@j_derivs, map($dtree->{j_data}[0]{phrase}[$_], @$deriv));
            }
            foreach my $i_p (@{$match->{i_phrases}}, map($dtree->{i_data}[0]{phrase}[$_], @{$match->{i_p_add}})) {
                foreach my $j_p (@{$match->{j_phrases}}, map($dtree->{j_data}[0]{phrase}[$_], @{$match->{j_p_add}})) {
                    if (defined $i_p->{extend} || defined $j_p->{extend}) {
                        $matrix->{$j_p->{pnum}}{$i_p->{pnum}}{mark} = "<font color=\"Black\">□</font>";
                    } else {
                        $matrix->{$j_p->{pnum}}{$i_p->{pnum}}{mark} = "<font color=\"Black\">■</font>";
                    }
                }
                foreach my $j_p (@j_derivs) {
                    $matrix->{$j_p->{pnum}}{$i_p->{pnum}}{mark} = "<font color=\"Black\">□</font>";
                }
            }
            foreach my $i_p (@i_derivs) {
                foreach my $j_p (@{$match->{j_phrases}}, map($dtree->{j_data}[0]{phrase}[$_], @{$match->{j_p_add}}), @j_derivs) {
                    $matrix->{$j_p->{pnum}}{$i_p->{pnum}}{mark} = "<font color=\"Black\">□</font>";
                }
            }
        }
    }

    for (my $i = 0; $i <= @i_tree_buffer; $i++) {
        for (my $j = 0; $j <= @j_tree_buffer; $j++) {
            $result .= sprintf ("%%%% 2 %d %d bgcolor=#EEEEEE\n", $j+1, $i+1) if (($i == 0 && $j != @j_tree_buffer && $j % 2 == 0) ||
                                                                          ($i != 0 && $j == @j_tree_buffer && $i % 2 == 0) ||
                                                                          ($i != 0 && $j != @j_tree_buffer && ($i % 2 == 0 || $j % 2 == 0)));
        }
    }

    foreach my $r (keys %{$matrix}) {
        foreach my $c (keys %{$matrix->{$r}}) {
            my @options;
            while (my ($key, $value) = each(%{$matrix->{$r}{$c}})) {
                next if ($key eq "mark" || $key eq "bgcolor_order");
                push (@options ,"$key=$value");
            }
            $result .= sprintf ("%%%% 2 %d %d %s\n", $r+1, $c+2, join(" ", @options));
            $result .= "$matrix->{$r}{$c}{mark}\n" if ($matrix->{$r}{$c}{mark} ne "");
        }
    }
    return $result;
}

sub print_help {
    print STDERR "Usage: $0 <xml-file>\n";
    print STDERR "You need TableDisplay.pm to output html file.\n";
    print STDERR "   e.g. perl -I/somewhere/the/module/exist $0\n";
    print STDERR "Also, you need viewer.css placed in the same directory of the html file.\n";
    exit;
}

&main();
