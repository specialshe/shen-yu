0.overview of KyotoEBMT system and this project
=======
KyotoEBMT system is a dependency-tree-based translate system. To create corpus in this system for example from Japanese to English, first parsing Japanese side, then parsing English side, At last align them together. This project modifies both parsing results for the better use by KyotoEBMT system.


1.How to use this project
==

First It needs get into the directory

>cd utls_private

For the visualazation of original parsing trees. You will get lots of .html files for the visualazation

>perl xml2web.pl bitext_m_3188.xml

To a better parsing tree

>perl instrictipon.pl 

For the visualazation of modified parsing trees. You will get lots of .html files for the visualazation, for example NTCIR-7-JE-1593502a.html corresponds to NTCIR-7-JE-1593502.html

>perl xml2web.pl bitext_m_3188a.xml

2.Details of some examples 
====
open NTCIR-7-JE-1593502.html. Bottom is 
