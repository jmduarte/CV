import bibtexparser

if __name__ == "__main__":
    aux_lines = []

    external = True
    if external:
        aux_file_name = "cv_duarte_javier.aux"
    else:
        aux_file_name = "publist_biobib.aux"

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
    with open(aux_file_name) as aux_file:
        aux_lines = aux_file.readlines()
        for line in aux_lines:
            if "abx@aux@number" in line:
                n = line.split("{")[-1][:-2]
                section = int(line.split("{")[3][:-1])
                key = line.split("{")[2][:-1]
                if section == 1:
                    prefix = "A.I."
                elif section == 2:
                    prefix = "A.II."
                elif section == 3:
                    prefix = "A.III."
                elif section == 4:
                    prefix = "A.IV."
                elif section == 5:
                    prefix = "B.I."
                elif section == 6:
                    prefix = "B.IV."
                elif section == 7:
                    prefix = "C."
                if external: 
                    prefix = ""
                name = prefix + n
                for l in bib_database.entries:
                    if l["ID"] == key and "keywords" in l and "career" in l["keywords"]:
                        if "doi" in l:
                            url = f"https://doi.org/{l['doi']}"
                        elif "eprint" in l:
                            url = f"https://arxiv.org/abs/{l['eprint']}"
                        elif "url" in l:
                            url = l["url"]
                        else:
                            print("WARNING: no URL found")
                        print(
                            f"\ifthenelse{{\equal{{#1}}{{{key}}}}}{{\href{{{url}}}{{\\textbf{{{name}}}}}}}{{}}%"
                        )
                        # n_ext = 0
                        # with open("cv_duarte_javier.aux") as ext_aux_file:
                        #     ext_aux_lines = ext_aux_file.readlines()
                        #     for ext_line in ext_aux_lines:
                        #         if "abx@aux@number" in ext_line and key in ext_line:
                        #             n_ext = int(ext_line.split("{")[-1][:-2])
                        #             break
                        # print("cp Javier_Duarte_Publications/*/%s.pdf Javier_Duarte_Publications/External/%s.pdf" % (name, n_ext))
