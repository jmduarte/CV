import bibtexparser
import os
from crossref.restful import Works
import requests
import tqdm
import copy

works = Works()
jhep_names = ['J. High Energy Phys.', 'JHEP']
epjc_names = ['Eur. Phys. J. C', 'EPJ C', 'EPJC']
prev_names = ['PRL', 'PRD', 'PRC', 'Phys. Rev. Lett.', 'Phys. Rev. D', 'Phys. Rev. C']
plb_names = ['Phys. Lett. B', 'PLB']
csbs_names = ['Comput. Softw. Big Sci.', 'CSBS']
sci_names = ['Science']
jinst_names = ['JINST', 'J. Instrum.']
nima_names = ['Nucl. Instrum. Meth. A', 'Nucl. Instrum. Methods Phys. Res. A']

journal_names_to_replace = {
    'Nucl. Instrum. Meth. A': 'Nucl. Instrum. Methods Phys. Res. A',
    'JINST': 'J. Instrum.',
    'JHEP': 'J. High Energy Phys.',
}

career_keys = ['Bornheim_2015','7581887','8069874','neurips2019_sonic','neurips2019_hbb','neurips2019_hls4ml',
               'CMS-DP-2018-046','CERN-LHCC-2020-004','CMS-PAS-EXO-17-026',
               'Duarte:2014soa','Anderson:2015tia','Anderson:2016tiu','Anderson:2016ygg',
               'Duarte:2017bbq','DiGuglielmo:2020eqx','Zlokapa:2019tkn','Duarte:2016wnw',
               'Duarte:2018ite','Duarte:2019fta','Khachatryan:2015pwa','Khachatryan:2016epu',
               'Moreno:2019bmu','Moreno:2019neq','Anderson:2015gha','Sirunyan:2016iap',
               'Sirunyan:2017dgc','Sirunyan:2017eie','Sirunyan:2017nvi','Sirunyan:2018ikr',
               'Sirunyan:2018koj','Sirunyan:2018kst','Sirunyan:2018sgc','Sirunyan:2018xlo',
               'Sirunyan:2019pnb','Sirunyan:2019sgo','Sirunyan:2019vgj','Sirunyan:2019vxa',
               'Summers:2020xiy','Sirunyan:2020hwz','Duarte:2018bsd','Albertsson:2018maf',
               'Krupa:2020bwg','Iiyama:2020wap']

convert_to_proceedings = ['Albertsson:2018maf','Duarte:2016wnw']

# get entries from INSPIRE
with open('INSPIRE-CiteAll.bib') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

# get entries not on INSPIRE
with open('NOT_ON_INSPIRE.BIB') as bibtex_file:
    bib_database_more = bibtexparser.load(bibtex_file)

# combine them
bib_database.entries.extend(bib_database_more.entries)

# prepare empty databases for proceedings and other
bib_database_other = copy.deepcopy(bib_database)
bib_database_other.entries = []

bib_database_proceedings = copy.deepcopy(bib_database)
bib_database_proceedings.entries = []

# loop over main database entries
t = tqdm.tqdm(bib_database.entries, total=len(bib_database.entries))
for l in t:
    t.set_description('Processing key {}'.format(l['ID']))
    t.refresh() # to show immediately the update

    # only first page
    if 'pages' in l and '-' in l['pages']:
        l['pages'] = l['pages'].split('-')[0]

    # add recent and career kewords
    add_recent_keyword = (int(l['year']) >= 2020) or (int(l['year']) == 2019 and 'month' in l and int(l['month']) >= 7)
    add_career_keyword = l['ID'] in career_keys
    keywords_to_add = []
    if add_recent_keyword:
        keywords_to_add.append('recent')
    if add_career_keyword:
        keywords_to_add.append('career')
    l['keywords'] = ','.join(keywords_to_add)

    # convert some entries to proceedings
    if l['ID'] in convert_to_proceedings:
        l['ENTRYTYPE'] = 'inproceedings'

    # check if publication
    is_publication = 'doi' in l and 'journal' in l and l['ENTRYTYPE'].lower() == 'article'

    # separate publications, proceedings, and other
    if not is_publication:
        if l['ENTRYTYPE'].lower() == 'inproceedings':
            bib_database_proceedings.entries.append(l)
        else:
            bib_database_other.entries.append(l)
        bib_database.entries.remove(l)
        continue

    # replace journal names with correct ISO4 abbreviation
    if l['journal'] in journal_names_to_replace.keys():
        l['journal'] = journal_names_to_replace[l['journal']]

    # remove weird PUBDB dois without journals
    if 'doi' in l and 'PUBDB' in l['doi']:
        if 'journal' not in l:
            del l['doi']
        else:
            # to fix doi
            r = requests.get('https://inspirehep.net/api/doi/{}'.format(l['doi']))
            rjson = r.json()
            for mdoi in rjson['metadata']['dois']:
                if l['doi'] != mdoi['value']:
                    l['doi'] = mdoi['value']
                    break

    # add publication month detail
    if l['journal'] in jhep_names:
        l['month'] = l['volume']
    elif l['journal'] in epjc_names:
        if 'number' in l:
            l['month'] = l['number']
        else:
            record = works.doi(l['doi'])
            pub = 'published-online'
            l['year'] = str(record[pub]['date-parts'][0][0])
            l['month'] = str(record[pub]['date-parts'][0][1])
    elif l['journal'] in prev_names+csbs_names+jinst_names+sci_names:
        record = works.doi(l['doi'])
        pub = 'published-online'
        l['year'] = str(record[pub]['date-parts'][0][0])
        l['month'] = str(record[pub]['date-parts'][0][1])
    elif l['journal'] in plb_names:
        record = works.doi(l['doi'])
        pub = 'published-print'
        l['year'] = str(record[pub]['date-parts'][0][0])
        l['month'] = str(record[pub]['date-parts'][0][1])

# export 3 bib files (publications, proceedings, other)
with open('INSPIRE_publications.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database, bibtex_file)
with open('INSPIRE_proceedings.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database_proceedings, bibtex_file)
with open('INSPIRE_other.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database_other, bibtex_file)
