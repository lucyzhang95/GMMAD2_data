import os
import uuid

import csv
import biothings_client
from collections.abc import Iterator
import itertools

"""
column names with index: {0: 'id', 1: 'g_micro', 2: 'organism', 3: 'g_meta', 4: 'metabolic', 5: 'pubchem_compound', 6: 'pubchem_id', 7: 'formula', 8: 'kegg_id', 9: 'tax_id', 10: 'phylum', 11: 'class', 12: 'order', 13: 'family', 14: 'genus', 15: 'species', 16: 'species_id', 17: 'source', 18: 'smiles_sequence', 19: 'HMDBID', 20: 'Origin'}
"""


def line_generator(file_path):
    with open(file_path, "r") as in_f:
        reader = csv.reader(in_f)
        # skip the header
        next(reader)
        for line in reader:
            yield line


def assign_col_val_if_available(node, key, val, transform=None):
    if val and val != "not available":
        node[key] = transform(val) if transform else val


def get_taxon_info(file_path) -> Iterator[dict]:
    taxids = [line[9] for line in line_generator(file_path)]
    taxids = set(taxids)
    t = biothings_client.get_client("taxon")
    taxon_info = t.gettaxa(taxids, fields=["scientific_name", "parent_taxid", "lineage", "rank"])
    yield taxon_info


def create_object_node(file_path):
    for line in line_generator(file_path):
        object_node = {
            "id": None,
            "name": line[5].lower(),
            "type": "biolink:ChemicalEntity"
        }

        assign_col_val_if_available(object_node, "pubchem_cid", line[6], int)
        assign_col_val_if_available(object_node, "kegg", line[8])
        assign_col_val_if_available(object_node, "hmdb", line[19])
        assign_col_val_if_available(object_node, "chemical_formula", line[7])
        assign_col_val_if_available(object_node, "smiles", line[18])

        if "pubchem_cid" in object_node:
            object_node["id"] = f"PUBCHEM.COMPOUND:{object_node['pubchem_cid']}"
        elif "kegg" in object_node:
            object_node["id"] = f"KEGG.COMPOUND:{object_node['kegg']}"
        elif "hmdb" in object_node:
            object_node["id"] = f"HMDB:{object_node['hmdb']}"
        else:
            object_node["id"] = str(uuid.uuid4())

        return object_node


def create_subject_node(file_path):
    taxon_info = {int(taxon["query"]): taxon for obj in get_taxon_info(file_path) for taxon in obj if "notfound" not in taxon.keys()}

    for line in line_generator(file_path):
        subject_node = {
            "id": None,
            "name": line[2].lower(),
            "type": "biolink:OrganismalEntity"
        }

        assign_col_val_if_available(subject_node, "taxid", line[9], int)
        if "taxid" in subject_node:
            subject_node["id"] = f"taxid:{subject_node['taxid']}"
        else:
            subject_node["id"] = str(uuid.uuid4())

        if subject_node.get("taxid") in taxon_info:
            subject_node["scientific_name"] = taxon_info[subject_node["taxid"]]["scientific_name"]
            subject_node["parent_taxid"] = taxon_info[subject_node["taxid"]]["parent_taxid"]
            subject_node["lineage"] = taxon_info[subject_node["taxid"]]["lineage"]
            subject_node["rank"] = taxon_info[subject_node["taxid"]]["rank"]

        return subject_node


def create_association_node(file_path):
    for line in line_generator(file_path):
        association_node = {
            "predicate": "biolink:associated_with",
            "infores": line[17]
        }
        if line[20] and line[20] != "Unknown":
            association_node["source"] = line[20].split(";")
        return association_node


def merge(file_path):
    association_nodes = create_association_node(file_path)
    subject_nodes = create_subject_node(file_path)
    object_nodes = create_object_node(file_path)

    combined_iterators = itertools.chain(association_nodes, subject_nodes, object_nodes)
    print(combined_iterators)
    return combined_iterators


def load_micro_meta_data():
    path = os.getcwd()
    file_path = os.path.join(path, "data", "micro_metabolic.csv")
    assert os.path.exists(file_path), f"The file {file_path} does not exist."
    merged_doc = merge(file_path)
    return merged_doc


if __name__ == "__main__":
    micro_meta_data = load_micro_meta_data()


