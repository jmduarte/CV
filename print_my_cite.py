import bibtexparser

if __name__ == "__main__":
    aux_lines = []

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
    with open("publist_biobib.aux") as aux_file:
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
