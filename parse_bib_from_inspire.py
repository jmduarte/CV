import bibtexparser
import os
from crossref.restful import Works
import requests
import tqdm
import copy
import time

works = Works()
jhep_names = ["J. High Energy Phys.", "JHEP"]
epjc_names = ["Eur. Phys. J. C", "EPJ C", "EPJC"]
prev_names = [
    "PRL",
    "PRD",
    "PRC",
    "Phys. Rev. Lett.",
    "Phys. Rev. D",
    "Phys. Rev. C",
    "Phys. Rev. Accel. Beams",
]
plb_names = ["Phys. Lett. B", "PLB"]
csbs_names = ["Comput. Softw. Big Sci.", "CSBS"]
sci_names = ["Science"]
jinst_names = ["JINST", "J. Instrum."]
nima_names = ["Nucl. Instrum. Meth. A", "Nucl. Instrum. Methods Phys. Res. A"]
iop_names = ["Mach. Learn.: Sci. Technol.", "Rep. Prog. Phys."]
nat_names = ["Nature", "Nat. Phys.", "Nature Phys.", "Nat. Mach. Intell.", "Sci. Data"]
fr_names = ["Front. AI", "Front. Big Data"]
spp_names = ["SciPost Phys."]
mlst_names = ["Mach. Learn.: Sci. Technol."]
ropp_names = ["Rep. Prog. Phys."]
tns_names = ["IEEE Trans. Nucl. Sci."]
qmi_names = ["Quantum Mach. Intell."]

journal_names_to_replace = {
    "Nucl. Instrum. Meth. A": "Nucl. Instrum. Methods Phys. Res. A",
    "JINST": "J. Instrum.",
    "JHEP": "J. High Energy Phys.",
    "Nature Phys.": "Nat. Phys.",
    "Rept. Prog. Phys.": "Rep. Prog. Phys.",
}

career_keys = [
    "7581887",
    "8069874",
    "Aarrestad:2020ngo",
    "Aarrestad:2021oeb",
    "Aarrestad:2021zos",
    "Agarwal:2023rwr",
    "Albertsson:2018maf",
    "Amaro:2023voyager",
    "Anderson:2015gha",
    "Anderson:2015tia",
    "Anderson:2016tiu",
    "Anderson:2016ygg",
    "Apresyan:2022tqw",
    "Baldi:2024reliable",
    "Banbury:2021mlperf",
    "Benelli:2022sqn",
    "Bhimij:2022xyn",
    "Black:2022cth",
    "Bornheim:2017gql",
    "Bornheim_2015",
    "Borras:2022opensource",
    "CERN-LHCC-2020-004",
    "CMS-DP-2018-046",
    "CMS-DP-2021-030",
    "CMS-DP-2022-041",
    "CMS-DP-2022-061",
    "CMS-DP-2023-037",
    "CMS-DP-2023-079",
    "CMS-PAS-EXO-17-026",
    "CMS-PAS-HIG-23-012",
    "CMS:2021juv",
    "CMS:2021yhb",
    "CMS:2022dwd",
    "CMS:2022nmn",
    "CMS:2022wjc",
    "CMS:2022wqf",
    "CMS:2024ake",
    "CMS:2024bvl",
    "CMS:2024ddc",
    "CMS:2024twn",
    "Campos:2023pkp",
    "Chen:2021euv",
    "Dawson:2022zbb",
    "Deiana:2021niw",
    "Dezoort:2021kfk",
    "DiGuglielmo:2020eqx",
    "DiGuglielmo:2021ide",
    "Duarte:2014soa",
    "Duarte:2016wnw",
    "Duarte:2017bbq",
    "Duarte:2018bsd",
    "Duarte:2018ite",
    "Duarte:2019fta",
    "Duarte:2020ngm",
    "Duarte:2022efficient",
    "Duarte:2022hdp",
    "Duarte:2022job",
    "Elabd:2021lgo",
    "Fahim:2021cic",
    "Govorkova:2021utb",
    "Hao:2022zns",
    "Harris:2022qtm",
    "Hawks:2021ruw",
    "Heintz:2020soy",
    "Huang:2023bny",
    "Huerta:2022kgj",
    "Hussain:2022faststamp",
    "Iiyama:2020wap",
    "Jawahar:2021vyu",
    "John:2020sak",
    "Kansal:2020svm",
    "Kansal:2021cqp",
    "Kansal:2022spb",
    "Kansal:2023joss",
    "Kasieczka:2021xcg",
    "Khachatryan:2015pwa",
    "Khachatryan:2016epu",
    "Krupa:2020bwg",
    "Li:2023xhj",
    "Li:2024xpw",
    "McDermott:2023neural",
    "Miao:2024oqy",
    "Mokhtar:2021bkf",
    "Mokhtar:2022pwm",
    "Mokhtar:2023fzl",
    "Moreno:2019bmu",
    "Moreno:2019neq",
    "Odagiu:2024bkp",
    "Orzari:2021suh",
    "Orzari:2023zrh",
    "Pappalardo:2022nxk",
    "Pata:2021oez",
    "Pata:2022wam",
    "Pata:2023rhh",
    "Rankin:2020usv",
    "Shanahan:2022ifi",
    "Shenoy:2023ros",
    "Sirunyan:2016iap",
    "Sirunyan:2017dgc",
    "Sirunyan:2017eie",
    "Sirunyan:2017nvi",
    "Sirunyan:2018ikr",
    "Sirunyan:2018koj",
    "Sirunyan:2018kst",
    "Sirunyan:2018sgc",
    "Sirunyan:2018xlo",
    "Sirunyan:2019pnb",
    "Sirunyan:2019sgo",
    "Sirunyan:2019vgj",
    "Sirunyan:2019vxa",
    "Sirunyan:2020hwz",
    "Summers:2020xiy",
    "Thais:2022iok",
    "Touranakou:2022qrp",
    "Tsan:2021brw",
    "Weng:2023tailor",
    "Weng:2024fkeras",
    "Wozniak:2020",
    "Zlokapa:2019tkn",
    "neurips2019_hbb",
    "neurips2019_hls4ml",
    "neurips2019_sonic",
]

convert_to_proceedings = []

with open("bib_publications.bib") as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

with open("bib_refproceedings.bib") as bibtex_file:
    bib_database_refproceedings = bibtexparser.load(bibtex_file)

with open("bib_proceedings.bib") as bibtex_file:
    bib_database_proceedings = bibtexparser.load(bibtex_file)

with open("bib_other.bib") as bibtex_file:
    bib_database_other = bibtexparser.load(bibtex_file)

# loop over all database entries
t = tqdm.tqdm(
    bib_database.entries
    + bib_database_refproceedings.entries
    + bib_database_proceedings.entries
    + bib_database_other.entries,
    total=len(
        bib_database.entries
        + bib_database_refproceedings.entries
        + bib_database_proceedings.entries
        + bib_database_other.entries
    ),
)
for l in t:
    t.set_description("Processing key {}".format(l["ID"]))
    t.refresh()  # to show immediately the update

    # only first page
    if "pages" in l and "-" in l["pages"]:
        l["pages"] = l["pages"].split("-")[0]

    # convert some entries to proceedings
    if l["ID"] in convert_to_proceedings:
        l["ENTRYTYPE"] = "inproceedings"

    # check if publication
    is_publication = (
        "doi" in l and "journal" in l and l["ENTRYTYPE"].lower() == "article"
    )

    # replace journal names with correct ISO4 abbreviation
    if is_publication and l["journal"] in journal_names_to_replace.keys():
        l["journal"] = journal_names_to_replace[l["journal"]]

    # remove weird PUBDB dois without journals
    if "doi" in l and "PUBDB" in l["doi"]:
        if "journal" not in l:
            del l["doi"]
        else:
            # to fix doi
            r = requests.get("https://inspirehep.net/api/doi/{}".format(l["doi"]))
            rjson = r.json()
            for mdoi in rjson["metadata"]["dois"]:
                if l["doi"] != mdoi["value"]:
                    l["doi"] = mdoi["value"]
                    break

    # add publication month detail if it does't exist already
    if is_publication and ("day" not in l or "month" not in l or "year" not in l):
        # time.sleep(1)
        if (
            l["journal"]
            in jhep_names
            + epjc_names
            + prev_names
            + csbs_names
            + jinst_names
            + spp_names
            + mlst_names
            + fr_names
            + ropp_names
            + qmi_names
        ):
            record = works.doi(l["doi"])
            pub = "published-online"
            l["year"] = str(record[pub]["date-parts"][0][0])
            l["month"] = str(record[pub]["date-parts"][0][1])
            if len(record[pub]["date-parts"][0]) > 2:
                l["day"] = str(record[pub]["date-parts"][0][2])
            else:
                l["day"] = "1"
        elif l["journal"] in sci_names + nat_names + nima_names + tns_names:
            record = works.doi(l["doi"])
            pub = "published"
            l["year"] = str(record[pub]["date-parts"][0][0])
            l["month"] = str(record[pub]["date-parts"][0][1])
            if len(record[pub]["date-parts"][0]) > 2:
                l["day"] = str(record[pub]["date-parts"][0][2])
            else:
                l["day"] = "1"
        elif l["journal"] in plb_names:
            record = works.doi(l["doi"])
            pub = "published-print"
            l["year"] = str(record[pub]["date-parts"][0][0])
            l["month"] = str(record[pub]["date-parts"][0][1])
            if len(record[pub]["date-parts"][0]) > 2:
                l["day"] = str(record[pub]["date-parts"][0][2])
            else:
                l["day"] = "1"
        else:
            record = works.doi(l["doi"])
            raise RuntimeError(
                "Unknown journal type for date lookup:\n{l}\n{record}".format(
                    l=l, record=record
                )
            )

    # add recent and career kewords
    add_recent_keyword = (int(l["year"]) >= 2023) or (
        int(l["year"]) == 2022
        and "month" in l
        and int(l["month"]) >= 8
        and "day" in l
        and int(l["day"]) >= 1
    )
    add_career_keyword = l["ID"] in career_keys
    keywords_to_add = []
    if add_recent_keyword:
        keywords_to_add.append("recent")
    if add_career_keyword:
        keywords_to_add.append("career")
    if keywords_to_add:
        l["keywords"] = ",".join(keywords_to_add)
    else:
        if "keywords" in l:
            del l["keywords"]

    # add CMS contribution codes if missing
    if is_publication and add_recent_keyword and "contibutioncodes" not in l:
        if ("collaboration" in l and "CMS" in l["collaboration"]) or (
            "usera" in l and "CMS" in l["usera"]
        ):
            codes = [8, 9]
            l["contributioncodes"] = ", ".join([str(c) for c in codes])

# export 4 bib files
with open("bib_publications_update.bib", "w") as bibtex_file:
    bibtexparser.dump(bib_database, bibtex_file)

with open("bib_refproceedings_update.bib", "w") as bibtex_file:
    bibtexparser.dump(bib_database_refproceedings, bibtex_file)

with open("bib_proceedings_update.bib", "w") as bibtex_file:
    bibtexparser.dump(bib_database_proceedings, bibtex_file)

with open("bib_other_update.bib", "w") as bibtex_file:
    bibtexparser.dump(bib_database_other, bibtex_file)
