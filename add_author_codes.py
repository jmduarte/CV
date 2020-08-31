import bibtexparser
import os
from crossref.restful import Works
import requests
import tqdm
import copy

# author codes:
# https://docs.google.com/spreadsheets/d/1JEj7V-RBv4JBM_ApefYaV5nyz52qea8EabgtSa3vECA/edit#gid=0
#1	Conceptualization
#2	Data curation
#3	Formal Analysis
#4	Funding Acquisition
#5	Investigation
#6	Methodology
#7	Project Administration
#8	Resources
#9	Software
#10	Supervision
#11	Validation
#12	Visualization
#13	Writing-Original Draft
#14	Writing-Reviewing and Editing
#15	Other
author_codes = {'neurips2019_sonic': [1,2,9,12,13],
                'neurips2019_hbb': [1,2,6,9,10,12,13],
                'neurips2019_hls4ml': [1,2,6,9,12,13],
                'CERN-LHCC-2020-004': [9,13,14,15],
                'DiGuglielmo:2020eqx': [1,9,14],
                'Zlokapa:2019tkn': [4,14],
                'Duarte:2019fta': [1,2,9,12,13],
                'Moreno:2019bmu': [1,2,6,9,10,12,13],
                'Moreno:2019neq': [1,2,6,9,10,12,13],
                'Sirunyan:2019pnb': [7,8,9,10],
                'Sirunyan:2019sgo': [7,8,9,10],
                'Sirunyan:2019vgj': [7,8,9,10],
                'Sirunyan:2019vxa': [7,8,9,10],
                'Summers:2020xiy': [1,2,6,8,9,10,14],
                'Sirunyan:2020hwz': [1,2,6,8,9,10,12,13],
                'Krupa:2020bwg': [1,2,4,6,8,9,10,14],
                'Iiyama:2020wap': [1,2,6,9,10,14],
                'CMS': [8,9]
                }
with open('bib_publications.bib') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

# loop over main database entries
t = tqdm.tqdm(bib_database.entries, total=len(bib_database.entries))
for l in t:
    t.set_description('Processing key {}'.format(l['ID']))
    t.refresh() # to show immediately the update

    is_recent = (int(l['year']) >= 2020) or (int(l['year']) == 2019 and 'month' in l and int(l['month']) >= 7)
    if not is_recent:
        continue

    if l['ID'] in author_codes:
        codes = [str(c) for c in author_codes[l['ID']]]
    elif 'collaboration' in l and 'CMS' in l['collaboration'] or ('usera' in l and 'CMS' in l['usera']):
        codes = [str(c) for c in author_codes['CMS']]

    if 'note' in l and 'Author Contribution Code(s)' not in l['note']:
        # add to note
        l['note'] += ', \\textbf{{Author Contribution Code(s)}}: {0}'.format(', '.join(codes))
    elif 'note' in l and 'Author Contribution Code(s)' in l['note']:
        if 'Accepted by' in l['note'] or 'Erratum' in l['note']:
            # update note
            former_note = l['note'].split('\\textbf{Author Contribution Code(s)}')[0]
            l['note'] = former_note + '\\textbf{{Author Contribution Code(s)}}: {0}'.format(', '.join(codes))
        else:
            # just replace note
            l['note'] = '\\textbf{{Author Contribution Code(s)}}: {0}'.format(', '.join(codes))
    else:
        # define new note
        l['note'] = '\\textbf{{Author Contribution Code(s)}}: {0}'.format(', '.join(codes))

# export 3 bib files (publications, proceedings, other)
with open('bib_publications.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database, bibtex_file)
