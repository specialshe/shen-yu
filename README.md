0.overview of KyotoEBMT system and this project
=======
KyotoEBMT system is a dependency-tree-based translate system. To create corpus in this system for example from Japanese to English, first parsing Japanese side, then parsing English side, At last align them together. This project modifies both parsing results for the better use by KyotoEBMT system.


1.How to use this project
==

First It needs get into the directory

>cd utls_private

For the visualazation of original parsing trees. You will get lots of .html files for the visualazation (30seconds)

>perl xml2web.pl bitext_m_3188.xml

To a better parsing tree (10seconds)

>perl instrictipon.pl 

For the visualazation of modified parsing trees. You will get lots of .html files for the visualazation, for example NTCIR-7-JE-1593502a.html corresponds to NTCIR-7-JE-1593502.html

>perl xml2web.pl bitext_m_3188a.xml (30seconds)

2.Details of some examples 
====
open NTCIR-7-JE-1593502.html. Bottom is Japanese's parsing. For example, 図's parent is 26. 26's parent is に, に's parent is 示
す. なる's brother is 絶縁, and their's parent is 膜. In the left side, it is the parsing of English. It is displayed same as Japanese. The black square is alignment, for example,  "絶縁" aligns to "insulating", "膜"　aligns to "film".　It also exists 2-2 cases. for example, "からなる" aligns to "made of".

3.Extractable treelets
===
Still look at this example, "しめすように" aligns to "as shown in", and  "as shown in" is still a connected part or we could say treelet in English parsing. But look at a "からなる絶縁膜" aligns to "insulating film  made of ", which is seperated by "29". So it is not a treelet in English and we call it unextractable. A general idea of EBMT system, for example to translate  "xxしめすように" , we just replace the Japanese tree structure to English tree structure. And it becomes "as shown in xx". But if it aligns to separated parts, we do not know how to stick these parts to the parsing tree, becuase the older one just has one part. Why this problem will happen, it is beacause the parsing is done dependent and some parts are wrong, this program solve these parsing errors and solve unextractable treelets. NTCIR-7-JE-1593502a.html is new tree after motified. Because dependency become more complicated, for visulization, English could not be displayed by origen order. You should take the origen one for reference. The alignment is no different, "からなる絶縁膜" aligns to "insulating film  made of ", but "insulating film  made of " is now not seperate by "29". And you can also realize that "絶縁膜13上に" now depends on "形成", but the origen one depends on "なる". Of couse depends on "形成" is the better one.
