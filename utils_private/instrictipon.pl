use strict;
use utf8;
use Data::Dumper;
open(FILE,"<:encoding(utf8)","bitext_m_3188.xml");
binmode(STDIN, ':encoding(utf8)'); 
binmode(STDOUT, ':encoding(utf8)');
binmode(STDERR, ':encoding(utf8)'); 
my $needlength=2;
my $line;
my @mark1;
my @mark2;
my @tree1;
my @tree2;
my $length1;
my $length2;
my @align1;
my @align2;
my $lengthalign;
my $i;
my $j;
my $k;
my $mark1;
my @tongji;
my @cuowu;
my @align3;
my @where1;
my @where2;
my @document1;
while ($line=<FILE>)
{
  push(@document1,$line);
  if ($line=~ /<para_sentence.*>/)
  {
    @align1=();
	@align2=();
	@align3=();
	@tree1=();
	@tree2=();
	@mark1=();
	@mark2=();
	@tongji=();
	@cuowu=();
	$j=0;
	<STDIN>;
  }
  if ($line=~ /<i_data>/)
  {
    $mark1=1;
	$i=-1;
  }
  if ($line=~ /dpnd="(.+?)"/)
  {
    $i=$i+1;
    if ($mark1 eq 1)
	{
	  $tree1[$i]->[0]=$1;
	}
	if ($mark1 eq 2)
	{
	  $tree2[$i]->[0]=$1;
	}
	
  }
  if ($line =~ /pos="(.+?)"/)
  {
     if ($mark1 eq 1)
	 {
	   $tree1[$i]->[1]=$1;
	 }
	 if ($mark1 eq 2)
	 {
	   $tree2[$i]->[1]=$1;
	 }
  }
  if ($line =~ /lem="(.+?)"/)
  {
     if ($mark1 eq 1)
	 {
	   $tree1[$i]->[2]=$1;
	   if (($1 eq "する/する") && ($tree1[$i]->[0] eq $i-1) && ($tree1[$i-1]->[1]=~ /名詞/))
	   {
	     $tree1[$i-1]->[1]="動詞";
	   }
	 }
	 if ($mark1 eq 2)
	 {
	   $tree2[$i]->[2]=$1;
	 }
  }
  if ($line=~ /<j_data>/)
  {
    $mark1=2;
	$i=-1;
  }
  if ($line=~ /<match i_p="(.+?)" j_p="(.+?)">/)
  {
    $align1[$j]=$1;
	$align2[$j]=$2;
	$j=$j+1;
  }
  if ($line=~ /<\/para_sentence>/)
  {
   $length2=int(@tree2)-1;
   $length1=int(@tree1)-1;
   $lengthalign=$j-1;
   for $i (0..$length2)
   {
    $mark2[$i]=2;
   }
   for $i (0..$lengthalign)
   { 
     $align1[$i]=[split(" ",$align1[$i])];
	 $align2[$i]=[split(" ",$align2[$i])];
	 for $j (@{$align2[$i]})
	  {
	    $mark2[$j]=0;
	  }
   }
   for $i (0..$lengthalign)
   {
     for $j (@{$align1[$i]})
	 {
	  $where1[$j]=$i;
	 }
   }
   my $mark5=0;
   for $i (0..$lengthalign)
   {
     $mark5=0;
     for $j (@{$align1[$i]})
	 {
	    if ($where1[$j] ne $where1[$tree1[$j]->[0]])
		{
		  my $temp3;
		  $temp3=$align1[$i]->[$mark5];
		  $align1[$i]->[$mark5]=$align1[$i]->[0];
		  $align1[$i]->[0]=$temp3;
		  last;
		}
		$mark5=$mark5+1;
	 }
   }
   for $i (0..$lengthalign)
   {
    for $j (@{$align2[$i]})
	{
	  $where2[$j]=$i;
	}
   }
   for $i (0..$lengthalign)
   {
     $mark5=0;
     for $j (@{$align2[$i]})
	 {
	   if ($where2[$j] ne $where2[$tree2[$j]->[0]])
	   {
	     my $temp3;
		 $temp3=$align2[$i]->[$mark5];
		 $align2[$i]->[$mark5]=$align2[$i]->[0];
		 $align2[$i]->[0]=$temp3;
		 last;
	   }
	 }
   }
    #print Dumper \@where1;
	#print Dumper \@mark2;
	for $i (0..$lengthalign)
	{
	  for $j (@{$align1[$i]})
	  {
	    $mark1[$j]=1;
	  }
	  for $j (@{$align2[$i]})
	  {
	    $mark2[$j]=1;
	  }
	  push(@align3,$i);
	  &step(1);
	  for $j (@{$align1[$i]})
	  {
	    $mark1[$j]=0;
	  }
	  for $j (@{$align2[$i]})
	  {
	    $mark2[$j]=0;
	  }
	  pop(@align3);
	}
	print "\n";
	for $i (@cuowu)
	{
	  my $mark3;
	  @mark1=();
	  $mark3=&xiangxin($i);
	  &writeback();
	}
	for $i (1..$needlength)
	{
	  print $tongji[$i]->[0]," ",$tongji[$i]->[1],"\n";
	}
	@document1=();
	#last;
  }
}
sub writeback()
{
  my $line;
  my $mark1;
  my $i;
  open(FILE2,">:encoding(utf8)","1.xml");
  for $line (@document1)
  {
    if ($line=~ /<i_data>/)
	{
	  $mark1=1;
	  $i=-1;
	}
	if ($line=~ /<j_data>/)
    {
      $mark1=2;
      $i=-1;	  
    }
	if ($line=~ /dpnd="(.+?)"/)
  {
    $i=$i+1;
    if ($mark1 eq 1)
	{
	  $line=~ s/dpnd=".+?"/dpnd="$tree1[$i]->[0]"/;
	}
	if ($mark1 eq 2)
	{
	  $line=~ s/dpnd=".+?"/dpnd="$tree2[$i]->[0]"/;
	}
  }
  print FILE2 $line;
 }
 close (FILE2);
}
sub xiangxin()
{
  my $i;
  my $j;
  my $flag3=shift;
  my $flag4=0;
  my $flag5;
  for $i (@{$flag3})
  {
    for $j (@{$align1[$i]})
	{
	  $mark1[$j]=1;
	}
  }
  my $flag6=0;
  for $i (@{$flag3})
  {
    for $j (@{$align1[$i]})
	{
	  if (($mark1[$tree1[$j]->[0]] ne 1) || ($tree1[$j]->[0] eq -1))
	  {
	    $flag5=$tree1[$j]->[0];
	  }
	  if (($tree1[$j]->[1]) =~ /動詞/)
	  {
	    $flag4=$flag4+1;
	  }
	  if (($tree1[$j]->[2] eq "に/に") || ($tree1[$j]->[2] eq "と/と") || ($tree1[$flag5]->[2] eq "も/も"))
	  {
	    $flag6=1;
	  }
	}
  }
  if ($flag6 ne 1) {$flag4=0;}
  print Dumper @mark1;
  while (($tree1[$flag5]->[2] ne "と/と") && ($tree1[$flag5]->[2] ne "も/も") && ($tree1[$flag5]->[2] ne "に/に") &&($flag5 ne "-1") && ($tree1[$flag5+1]->[2] ne "、/、"))
  {
    if ($tree1[$flag5]->[1] =~ /動詞/)
	{
	   #print Dumper $flag5;
	   $flag4=$flag4+1;
	}
	$flag5=$tree1[$flag5]->[0];
  }
  print $flag5,"\n";
  print $flag4,"\n";
 <STDIN>;
  if ($flag4<2)
  {
    my $temp1;
    for $i (@{$flag3})
	{
	  my $mark4=0;
	  for $j (@{$align1[$i]})
	  {
	    if ($where1[$j] ne $where1[$tree1[$j]->[0]])
		{
		  $temp1=$where1[$tree1[$j]->[0]];
		}
		if ($tree1[$j]->[0] eq "-1")
		{
		  $mark4=1;
		}
	  }
	  if ($mark4 eq 0)
	  {
	  for $j (@{$align2[$i]})
	  {
	    #print Dumper $j;
	   # print Dumper $tree2[$j];
		#print Dumper $align2[$temp1]->[0];
		#<STDIN>;
		if ($where2[$j] ne $where2[$tree2[$j]->[0]])
		{
		 my $temp2=$tree2[$j]->[0];
	    $tree2[$j]->[0]=$align2[$temp1]->[0];
		if (&lays2($align2[$temp1]->[0],$j))
		{
		  $tree2[$align2[$temp1]->[0]]->[0]=$temp2;
		}
		}
	  }
	  }
	}
  }
  else
  {
    my $temp1;
	
    for $i (@{$flag3})
	{
	  my $mark4=0;
	  for $j (@{$align2[$i]})
	  {
	     if ($where2[$j] ne $where2[$tree2[$j]->[0]])
		 {
		   $temp1=$where2[$tree2[$j]->[0]];
		 }
		 if ($tree2[$j]->[0] eq "-1")
		 {
		   $mark4=1;
		 }
	  }
	  if ($mark4 eq 0)
	  {
	   for $j (@{$align1[$i]})
	   {
	    if ($where1[$j] ne $where1[$tree1[$j]->[0]])
		{
		  my $temp2=$tree1[$j]->[0];
		 $tree1[$j]->[0]=$align1[$temp1]->[0];
		 #print $align1[$temp1]->[0],$j;
		 #  <STDIN>;
		 if (&lays($align1[$temp1]->[0],$j))
		 {		   
		   $tree1[$align1[$temp1]->[0]]->[0]=$temp2;
		 }
		}
	   }
	  }
	}
  }
}
sub lays2()
{
  my $i=shift;
  my $j=shift;
  while ($i ne -1)
  {
    $i=$tree2[$i]->[0];
	if ($i eq $j)
	{
	  return 1;
	}
  }
  return 0;
}
sub lays()
{
  my $i=shift;
  my $j=shift;
  while ($i ne -1)
  {
    $i=$tree1[$i]->[0];
	if ($i eq $j)
	{
	  return 1;
	}
  }
  return 0;
}
sub step()
{
  my $now=shift;
  if ($now eq $needlength+1) {return;}
  for $i (0..$lengthalign)
  {
    my $flag2=-1;
    for $j (@{$align1[$i]})
	{
      if (($mark1[$tree1[$j]->[0]] eq 1) && ($mark1[$j] ne 1) && ($tree1[$j]->[0] ne -1))
	  {
	    $flag2=$i;
	  }
	}
    if ($flag2 ne -1) 
    {
	   for $j (@{$align1[$flag2]})
	   {
	     $mark1[$j]=1;
	   }
	   for $j (@{$align2[$i]})
	  {
	    $mark2[$j]=1;
	  }
	  push(@align3,$i);
	  my $flag1;
	  for $i (0..$length2)
	{
	  if ($mark2[$i] eq 1)
	  {
	    if ((($mark2[$tree2[$i]->[0]] ne 1) && ($mark2[$tree2[$i]->[0]] ne 2)) ||($tree2[$i]->[0] eq -1))
		{
		  $flag1=$flag1+1;
		}
	  }
	}
	if ($flag1 <= 1)
	{
	  $tongji[$now]->[0]+=1;
	  $tongji[$now]->[1]+=1;
	  #print "yes";
	}
	else
	{
	 my $str1;
    #print "no\n";
	 for $i (0..$length2)
	 {
	   if ($mark2[$i] eq 1)
	   {
	     $str1=$str1.$i." ";
	   }
	 }
	 push(@cuowu,[@align3]);
	 $tongji[$now]->[1]+=1;
	}
	   #print Dumper @{$align1[$flag2]};
	  # print Dumper \@mark1;
	   #<STDIN>;
	   &step($now+1);
	   for $j (@{$align1[$flag2]})
	   {
	     $mark1[$j]=0;
	   }
	   for $j (@{$align2[$i]})
	  {
	    $mark2[$j]=0;
	  }
	  pop(@align3);
    }	
  }
}