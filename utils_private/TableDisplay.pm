package TableDisplay;

##################################################
# 
# Version 0.1 (2007/04/24 by Nakazawa)
# 
##################################################

use utf8;
use strict;

my %coordinate;
my %inline;
my %table_f;

my %max_row;
my %max_col;
my $options;
my $features;

sub new
{
    my ($class, $f) = @_;
    my $this;
    $this->{feature} = $f;
    while (my ($key, $value) = each (%{$this->{feature}})) {
	$features .= "$key=$value&";
    }
    bless $this;
    return $this;
}

sub read_text
{
    my ($input) = @_;
    my ($index, $r, $c);

    %coordinate = ();;
    %inline = ();
    %table_f = ();
    %max_row = ();
    %max_col = ();
    $options = {};

    foreach (split(/\n/, $input)) {
	chomp;

	# セルごとの指定
	if (/^\%\% ([\d\.]+) ([\d\.]+) ([\d\.]+)\s*(.*)$/) {
	    $index = $1;
	    $r = $2;
	    $c = $3;
	    foreach my $option (split(/\s+/, $4)) {
		if ($option =~ /^(.+?)=(.+)$/) {
		    my $key = $1;
		    my $value = $2;
		    $value =~ s/^\"//;
		    $value =~ s/\"$//;
		    next if ($key eq "" || $value eq "");
		    $key =~ tr/[a-z]/[A-Z]/;
		    $coordinate{$index}{$r}{$c}{option}{$key} = $value;
		}
	    }
	}

	# テーブルに対するフィーチャー
	elsif (/^\%\% ([\d\.]+)\s*(.*)$/) {
	    my $table_index = $1;
	    foreach my $option (split(/\s+/, $2)) {
		my ($key, $value) = split(/=/, $option);
		next if ($key eq "" || $value eq "");
		$key =~ tr/[a-z]/[A-Z]/;
		$table_f{$table_index}{$key} = $value;
	    }
	}

	# ページ内リンク
	elsif (/^\%\% LABEL=(.*)$/i) {
	    $index = $1;
	    $r = 0;
	    $c = 0;
	}

	# ページ全体のフィーチャー
	elsif (/^\%\% (.*)$/) {
	    my $key_old = "";
	    foreach my $option (split(/\s+/, $1)) {
		my ($key, $value) = split(/=/, $option);
		next if ($key eq "");
		if ($value eq "") {
		    $value = $key;
		    $key = $key_old;
		}
		$key =~ tr/[a-z]/[A-Z]/;
		$options->{$key} .= "$value ";
		$key_old = $key;
	    }
	}

	# セルの内容
	else {
	    if ($r == 0 && $c == 0) {
		$inline{$index} .= $_;
		$inline{$index} =~ s/\'/\\\'/g;
		$inline{$index} =~ s/\"//g;
	    } else {
		if ($coordinate{$index}{$r}{$c}{option}{PRE}) {
		    s/\&/\&amp\;/g;
		    s/\ /\&nbsp\;/g;
		    s/\</\&lt\;/g;
		    s/\>/\&gt\;/g;
		    s/\"/\&quot\;/g;
		    $coordinate{$index}{$r}{$c}{string} .= "$_<BR>";
		} else {
		    $coordinate{$index}{$r}{$c}{string} .= $_;
		}
	    }

	    # 最大値
	    $max_row{$index} = $r if ($r > $max_row{$index});
	    $max_col{$index} = $c if ($c > $max_col{$index});
	}
    }

    foreach my $key (keys %$options) {
	$options->{$key} =~ s/\s+$//;
	$options->{$key} =~ s/^\s+//;
	$options->{$key} =~ s/\s+/ /g;
    }
}

sub convert
{
    my ($this, $input, $option) = @_;
    &read_text($input);

    my $html;

    unless (defined $option->{no_header}) {
	$html .= sprintf (qq(<html>\n));
	$html .= sprintf (qq(<head>\n));
	$html .= sprintf (qq(<meta http-equiv="content-type" content="text/html;charset=utf-8">\n));
	$html .= sprintf (qq(<link rel="stylesheet" href="viewer.css" type="text/css" media="all">\n));
	$html .= sprintf (qq(<title>$options->{TITLE}</title>\n));
	$html .= sprintf (qq(</head>\n));
	$html .= sprintf (qq(<body>\n));
    }
    unless (defined $option->{no_overlib}) {
	$html .= sprintf (qq(<div id="overDiv" style="position:absolute; visibility:hidden; z-index:1000;"></div><script language="JavaScript" src="overlib.js"></script>));
    }
    $html .= sprintf (qq(<h2>$options->{TITLE}</h2>\n)) if (defined $options->{TITLE});
    $html .= sprintf << "END_OF_JAVA";
    <script type="text/javascript"><!--
    function show_inline_data(label, docbody)
    {
	var win;
	win = window.open("", "TableDisplay", "toolbar=no, location=no, directories=no, status=yes, menubar=no, scrollbars=yes, resizable=yes");
	win.focus();
	win.document.open();
	win.document.write("<HTML><HEAD><TITLE>"+label+"</TITLE></HEAD><BODY>");
	win.document.write(docbody);
	win.document.write("</BODY></HTML>");
	win.document.close();
    }
    //--></script>
END_OF_JAVA

    foreach my $index (sort {$a <=> $b} keys %coordinate) {
	    
	my @table_atributes;
	foreach my $key (keys %{$table_f{$index}}) {
	    push @table_atributes, qq($key="$table_f{$index}{$key}");
	}

	$html .= sprintf (qq(<table border="0" style="border-collapse: collapse; empty-cells: show;" ));
	$html .= sprintf (join ' ', @table_atributes);
	$html .= sprintf (qq(><tr>));

	$max_row{$index} = 1 unless (defined $max_row{$index});
	$max_col{$index} = 1 unless (defined $max_col{$index});

	my $skip_matrix;

	for (my $r = 1; $r <= $max_row{$index}; $r++) {
	    for (my $c = 1; $c <= $max_col{$index}; $c++) {

		next if (defined $skip_matrix->{$r}{$c});

		my $cellheader = "";
		my $cellfooter = "";

		# オプションの処理

		delete $coordinate{$index}{$r}{$c}{option}{PRE} if (defined $coordinate{$index}{$r}{$c}{option}{PRE});

		# ジャンプ
		if (defined $coordinate{$index}{$r}{$c}{option}{A}) {
		    $cellheader .= qq(<a href="$ENV{'SCRIPT_NAME'}?fname=$this->{feature}{path}/$coordinate{$index}{$r}{$c}{option}{A}&$features" target="_blank">\n);
		    delete $coordinate{$index}{$r}{$c}{option}{A};
		    $cellfooter = "</a>\n$cellfooter";
		}
		# リンク
		elsif (defined $coordinate{$index}{$r}{$c}{option}{EXTERN}) {
		    if ($coordinate{$index}{$r}{$c}{option}{EXTERN} =~ /\?/) {
			$cellheader .= qq(<a href="$coordinate{$index}{$r}{$c}{option}{EXTERN}&$features" target="_blank">\n);
		    } else {
			$cellheader .= qq(<a href="$coordinate{$index}{$r}{$c}{option}{EXTERN}?$features" target="_blank">\n);
		    }
		    delete $coordinate{$index}{$r}{$c}{option}{EXTERN};
		    $cellfooter = "</a>\n$cellfooter";
		}
		# ページ内リンク 
		elsif (defined $coordinate{$index}{$r}{$c}{option}{LABEL}) {
		    $cellheader .= qq(<a href="javascript:void\(0\)" );
		    unless (defined $option->{no_overlib}) {
			$cellheader .= qq(onMouseOver="return overlib('$inline{$coordinate{$index}{$r}{$c}{option}{LABEL}}', ol_offsetx=-20, ol_textsize=2, ol_width=600)" );
			$cellheader .= qq(onMouseOut="return nd()" );
		    }
		    $cellheader .= qq(onClick="show_inline_data\('$coordinate{$index}{$r}{$c}{option}{LABEL}', '$inline{$coordinate{$index}{$r}{$c}{option}{LABEL}}'\) ">\n);
		    delete $coordinate{$index}{$r}{$c}{option}{LABEL};
		    $cellfooter = "</a>\n$cellfooter";
		}

		my @td_atributes;
		foreach my $key (keys %{$coordinate{$index}{$r}{$c}{option}}) {
		    push @td_atributes, qq($key="$coordinate{$index}{$r}{$c}{option}{$key}");
		    
		    # セルの結合
		    if ($key eq "COLSPAN") {
			for (my $i = 1; $i < $coordinate{$index}{$r}{$c}{option}{$key}; $i++) {
			    $skip_matrix->{$r}{$c+$i} = 1;
			}
		    }
		    if ($key eq "ROWSPAN") {
			for (my $i = 1; $i < $coordinate{$index}{$r}{$c}{option}{$key}; $i++) {
			    $skip_matrix->{$r+$i}{$c} = 1;
			}
		    }
		}

		$html .= sprintf (qq(<td ));
		$html .= sprintf (join ' ', @td_atributes);
		$html .= sprintf (qq(>));
		$html .= sprintf ($cellheader);
		$html .= sprintf (defined $coordinate{$index}{$r}{$c}{string} ? $coordinate{$index}{$r}{$c}{string} : qq(&nbsp;&nbsp;));
		$html .= sprintf ($cellfooter);
		$html .= sprintf (qq(</td>\n));
	    }
	    $html .= sprintf (qq(</tr>\n));
	}

	$html .= sprintf (qq(</table><br>\n));
    }

#     $html .= sprintf (qq(</body>\n));
#     $html .= sprintf (qq(</html>\n));
    return $html;
}

1;

