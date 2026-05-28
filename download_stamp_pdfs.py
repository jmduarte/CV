import bibtexparser
import requests
import os
from articledownloader.articledownloader import ArticleDownloader
import time
import platform

if __name__ == "__main__":

    downloader = ArticleDownloader(els_api_key="11acc1dbb49e1a44d49d46d48469a2f7")

    if platform.system().lower() == "linux":
        if platform.machine() == "arm64":
            cpdf = "./cpdf-binaries/Linux-ARM/cpdf"
        else:
            cpdf = "./cpdf-binaries/Linux-Intel-64bit/cpdf"
    elif platform.system().lower() == "darwin":
        if platform.machine() == "arm64":
            cpdf = "./cpdf-binaries/OSX-ARM/cpdf"
        else:
            cpdf = "./cpdf-binaries/OSX-Intel/cpdf"
    elif platform.system().lower() == "win32":
        cpdf = "./cpdf-binaries/Windows32bit/cpdf.exe"

    aux_lines = []
    with open("publist_biobib.aux") as aux_file:
        aux_lines = aux_file.readlines()

    with open("bib_publications.bib") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    with open("bib_reviews.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)
    with open("bib_bookchapters.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)
    with open("bib_refproceedings.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)
    with open("bib_proceedings.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)
    with open("bib_other.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)
    with open("bib_workinprogress.bib") as bibtex_file:
        bib_database_more = bibtexparser.load(bibtex_file)
    bib_database.entries.extend(bib_database_more.entries)

    for l in bib_database.entries:
        print("Checking %s" % l["ID"])
        if "keywords" in l and "career" in l["keywords"]:
            name = ""
            for line in aux_lines:
                if "bx@aux@number" in line and l["ID"] in line:
                    n = line.split("{")[-1][:-2]
                    section = int(line.split("{")[3][:-1])
                    if section == 1:
                        prefix = "A.I."
                        article_dir = "Javier_Duarte_Publications/Research_Articles"
                    elif section == 2:
                        prefix = "A.II."
                        article_dir = "Javier_Duarte_Publications/Reviews"
                    elif section == 3:
                        prefix = "A.III."
                        article_dir = "Javier_Duarte_Publications/Books_and_Book_Chapters"
                    elif section == 4:
                        prefix = "A.IV."
                        article_dir = "Javier_Duarte_Publications/Refereed_Conference_Proceedings"
                    elif section == 5:
                        prefix = "B.I."
                        article_dir = "Javier_Duarte_Publications/Other_Conference_Proceedings"
                    elif section == 6:
                        prefix = "B.IV."
                        article_dir = "Javier_Duarte_Publications/Additional_Products_of_Major_Research"
                    elif section == 7:
                        prefix = "C."
                        article_dir = "Javier_Duarte_Publications/Work_in_Progress"
                    name = prefix + n
                    os.makedirs(article_dir, exist_ok=True)
                    print("Destination file: %s/%s.pdf" % (article_dir, name))
                    break
            if (
                os.path.isfile("%s/%s.pdf" % (article_dir, name))
                and os.path.getsize("%s/%s.pdf" % (article_dir, name)) > 0
            ):
                continue

            print("Getting PDF URL for %s" % l["ID"])


            if "doi" in l:
                r = requests.get("https://doi.org/" + l["doi"])
                print("Redirected URL: %s" % r.url)                
                get_pdf_url = ""
                if "link.springer.com" in r.url:
                    get_pdf_url = r.url.replace("/article/", "/content/pdf/") + ".pdf"
                elif "link.aps.org" in r.url:
                    if "PhysRevD" in r.url:
                        get_pdf_url = r.url.replace("https://link.aps.org/doi/", "https://journals.aps.org/prd/pdf/")
                    elif "PhysRevLett" in r.url:
                        get_pdf_url = r.url.replace("https://link.aps.org/doi/", "https://journals.aps.org/prl/pdf/")                    
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
                    get_pdf_url = r.url.replace(
                        "/document/", "/stamp/stamp.jsp?tp=&arnumber="
                    )[:-1]
                elif "iopscience.iop.org" in r.url:
                    get_pdf_url = r.url + "/pdf"
                elif "scipost.org" in r.url:
                    get_pdf_url = r.url + "/pdf"
                elif "nature.com" in r.url:
                    get_pdf_url = r.url + ".pdf"
                elif "frontiersin.org" in r.url:
                    get_pdf_url = r.url.replace("/full", "/pdf")
                elif "dl.acm.org" in r.url:
                    get_pdf_url = r.url.replace("/doi/", "/doi/pdf/")
                elif "josstheoj.org" in r.url:
                    pages = r.url.split(".")[-1]
                    get_pdf_url = (
                        "https://www.theoj.org/joss-papers/"
                        + "joss."
                        + pages
                        + "/10.21105.joss."
                        + pages
                        + ".pdf"
                    )
                elif "pos.sissa.it" in r.url:
                    get_pdf_url = r.url + "/pdf"
                elif "epj-conferences.org" in r.url:
                    get_pdf_url = r.url + "/pdf"
            elif "url" in l:
                get_pdf_url = l["url"]
            elif "eprint" in l:
                get_pdf_url = f"https://arxiv.org/pdf/{l['eprint']}"
            else:
                print("WARNING: no URL found")
                break

            print("URL: %s" % get_pdf_url)
            if not (
                os.path.isfile("%s/%s_nostamp.pdf" % (article_dir, name))
                and os.path.getsize("%s/%s_nostamp.pdf" % (article_dir, name)) > 0
            ):
                print("Downloading %s" % l["ID"])
                if "elsevier" in get_pdf_url or "sciencedirect" in get_pdf_url:
                    with open(
                        "%s/%s_nostamp.pdf" % (article_dir, name), "wb"
                    ) as my_file:
                        b = downloader.get_pdf_from_doi(l["doi"], my_file, "elsevier")
                elif "iopscience" in get_pdf_url:
                    with open(
                        "%s/%s_nostamp.pdf" % (article_dir, name), "wb"
                    ) as my_file:
                        b = downloader.get_pdf_from_doi(l["doi"], my_file, "crossref")
                    if not b:
                        response = requests.get(get_pdf_url, stream=True)
                        with open(
                            "%s/%s_nostamp.pdf" % (article_dir, name), "wb"
                        ) as handle:
                            for data in response.iter_content():
                                handle.write(data)
                else:
                    response = requests.get(get_pdf_url, stream=True)
                    with open(
                        "%s/%s_nostamp.pdf" % (article_dir, name), "wb"
                    ) as handle:
                        for data in response.iter_content():
                            handle.write(data)
            else:
                print("Already downloaded %s" % l["ID"])

            print("Stamping %s" % l["ID"])
            stamp_page = 1
            if "iopscience" in get_pdf_url:
                stamp_page = 2
            command = (
                '%s -add-text "%s" -topright 20  %s/%s_nostamp.pdf %i -o %s/%s_stamp.pdf'
                % (
                    cpdf,
                    name,
                    article_dir,
                    name,
                    stamp_page,
                    article_dir,
                    name,
                )
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
