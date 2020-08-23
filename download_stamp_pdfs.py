import bibtexparser
import requests
import os
import tqdm
from articledownloader.articledownloader import ArticleDownloader
downloader = ArticleDownloader(els_api_key='11acc1dbb49e1a44d49d46d48469a2f7')

aux_lines = []
with open('publist_biobib.aux') as aux_file:
    aux_lines = aux_file.readlines()

with open('bib_publications.bib') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

article_dir = 'Journal_Articles'

t = tqdm.tqdm(bib_database.entries, total = len(bib_database.entries))
for l in t:
    if 'doi' in l and 'keywords' in l and 'recent' in l['keywords']:
        name = ''
        for line in aux_lines:
            if 'bx@aux@number' in line and l['ID'] in line:
                n = line.split('{')[-1][:-2]
                name = 'A.I.a.'+n
        if os.path.isfile('%s/%s.pdf'%(article_dir,name)): continue
        r = requests.get('https://doi.org/'+l['doi'])
        get_pdf_url = ''
        if 'https://link.springer.com/' in r.url:
            get_pdf_url = r.url.replace('/article/','/content/pdf/')+'.pdf'
        elif 'https://journals.aps.org/' in r.url:
            get_pdf_url = r.url.replace('/abstract/','/pdf/')
        elif 'https://linkinghub.elsevier.com/' in r.url:
            pdfname = '1-s2.0-'+r.url.split('/')[-1]+'-main.pdf'
            get_pdf_url = r.url.replace('https://linkinghub.elsevier.com/retrieve/','https://www.sciencedirect.com/science/article/')+'/pdfft?isDTMRedir=true&download=true'
        elif 'https://ieeexplore.ieee.org/' in r.url:
            get_pdf_url = r.url.replace('/document/','/stamp/stamp.jsp?tp=&arnumber=')[:-1]
        elif 'https://iopscience.iop.org/' in r.url:
            get_pdf_url = r.url+'/pdf'
        if get_pdf_url!='': l['pdf'] = get_pdf_url

        stamp_page = 1
        if 'elsevier' in r.url:
            with open('%s/%s.pdf'%(article_dir,name), 'wb') as my_file:
                b = downloader.get_pdf_from_doi(l['doi'], my_file, 'elsevier')
        elif 'iopscience' in r.url:
            stamp_page = 2
            with open('%s/%s.pdf'%(article_dir,name), 'wb') as my_file:
                b = downloader.get_pdf_from_doi(l['doi'], my_file, 'crossref')
        else:
            command = 'curl -o %s/%s.pdf "%s"'%(article_dir,name,get_pdf_url)
            print(command)
            value = os.system(command)
            if value!=0:
                print("ERROR")
                continue
        command = './cpdf-binaries/OSX-Intel/cpdf -add-text "%s" -topright 20  %s/%s.pdf %i -o %s/%s_text.pdf'%(name,article_dir,name,stamp_page,article_dir,name)
        value = os.system(command)
        if value!=0:
            print("ERROR")
            continue
        command = 'mv %s/%s_text.pdf %s/%s.pdf'%(article_dir,name,article_dir,name)
        value = os.system(command)
        if value!=0:
            print("ERROR")
            continue

