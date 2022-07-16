import bibtexparser
import requests
import os
from articledownloader.articledownloader import ArticleDownloader
import time
from sys import platform

if __name__ == '__main__':

    downloader = ArticleDownloader(els_api_key="11acc1dbb49e1a44d49d46d48469a2f7")

    if platform == "linux" or platform == "linux2":
        cpdf = "./cpdf-binaries/Linux-Intel-64bit/cpdf"
    elif platform == "darwin":
        cpdf = "./cpdf-binaries/OSX-Intel/cpdf"
    elif platform == "win32":
        cpdf = "./cpdf-binaries/Windows32bit/cpdf.exe"

    aux_lines = []
    with open("publist_biobib.aux") as aux_file:
        aux_lines = aux_file.readlines()

    with open("bib_publications.bib") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    article_dir = "Research_Articles"
    os.makedirs(article_dir, exist_ok=True)

    for l in bib_database.entries:
        print("Checking %s" % l["ID"])
        if "doi" in l and "keywords" in l and "recent" in l["keywords"]:
            name = ""
            for line in aux_lines:
                if "bx@aux@number" in line and l["ID"] in line:
                    n = line.split("{")[-1][:-2]
                    name = "A.I." + n
            if (
                os.path.isfile("%s/%s.pdf" % (article_dir, name))
                and os.path.getsize("%s/%s.pdf" % (article_dir, name)) > 0
            ):
                continue


            print("Getting PDF URL for %s" % l["ID"])
            r = requests.get("https://doi.org/" + l["doi"])
            get_pdf_url = ""
            if "link.springer.com" in r.url:
                get_pdf_url = r.url.replace("/article/", "/content/pdf/") + ".pdf"
            elif "journals.aps.org" in r.url:
                get_pdf_url = r.url.replace("/abstract/", "/pdf/")
            elif "linkinghub.elsevier.com" in r.url:
                pdfname = "1-s2.0-" + r.url.split("/")[-1] + "-main.pdf"
                get_pdf_url = (
                    r.url.replace(
                        "https://linkinghub.elsevier.com/retrieve/",
                        "https://www.sciencedirect.com/science/article/",
                    )
                    + "/pdfft?isDTMRedir=true&download=true"
                )
            elif "ieeexplore.ieee.org" in r.url:
                get_pdf_url = r.url.replace("/document/", "/stamp/stamp.jsp?tp=&arnumber=")[
                    :-1
                ]
            elif "iopscience.iop.org" in r.url:
                get_pdf_url = r.url + "/pdf"
            elif "scipost.org" in r.url:
                get_pdf_url = r.url + "/pdf"
            elif "nature.com" in r.url:
                get_pdf_url = r.url + ".pdf"
            elif "frontiersin.org" in r.url:
                get_pdf_url = r.url.replace("/full","/pdf")
                
            if (
                not (os.path.isfile("%s/%s_nostamp.pdf" % (article_dir, name))
                and os.path.getsize("%s/%s_nostamp.pdf" % (article_dir, name)) > 0)
            ):
                print("Downloading %s" % l["ID"])
                if "elsevier" in r.url:
                    with open("%s/%s_nostamp.pdf" % (article_dir, name), "wb") as my_file:
                        b = downloader.get_pdf_from_doi(l["doi"], my_file, "elsevier")
                elif "iopscience" in r.url:
                    with open("%s/%s_nostamp.pdf" % (article_dir, name), "wb") as my_file:
                        b = downloader.get_pdf_from_doi(l["doi"], my_file, "crossref")
                    if not b:
                        response = requests.get(get_pdf_url, stream=True)
                        with open("%s/%s_nostamp.pdf" % (article_dir, name), "wb") as handle:
                            for data in response.iter_content():
                                handle.write(data)
                else:
                    response = requests.get(get_pdf_url, stream=True)
                    with open("%s/%s_nostamp.pdf" % (article_dir, name), "wb") as handle:
                        for data in response.iter_content():
                            handle.write(data)

            print("Stamping %s" % l["ID"])
            stamp_page = 1
            if "iopscience" in r.url:
                stamp_page = 2
            command = '%s -add-text "%s" -topright 20  %s/%s_nostamp.pdf %i -o %s/%s_stamp.pdf' % (
                cpdf,
                name,
                article_dir,
                name,
                stamp_page,
                article_dir,
                name,
            )
            
            value = os.system(command)
            
            if value != 0:
                print("Error stamping %s" % l["ID"])
                os.system("rm  %s/%s_stamp.pdf" % (article_dir, name))
                print("Check for CAPTCHA?: %s" % get_pdf_url)
                continue

            if stamp_page > 1:
                command = "%s %s/%s_stamp.pdf %i-end -o %s/%s.pdf" % (
                    cpdf,
                    article_dir,
                    name,
                    stamp_page,
                    article_dir,
                    name,
                )
            else:
                command = "mv %s/%s_stamp.pdf %s/%s.pdf" % (
                    article_dir,
                    name,
                    article_dir,
                    name,
                )

            value = os.system(command)

            if value != 0:
                print("Error clipping/moving %s" % l["ID"])
                os.system("rm %s/%s.pdf" % (article_dir, name))

            if os.path.isfile("%s/%s_stamp.pdf" % (article_dir, name)):
                os.system("rm %s/%s_stamp.pdf" % (article_dir, name))

            time.sleep(5)
