import enum
import yaml
import os
from microCBR.kb import KB_Chaos
import logging

_LOGGER = logging.getLogger(__name__)


def generateKB_from_chaos(chaos_data_dir, chaos_management_file):

    f = open(chaos_management_file)
    data = f.read()
    f.close()
    chaos_manage = yaml.safe_load(data)

    chaos_types = os.listdir(chaos_data_dir)
    kb = dict()
    for chaos_type in chaos_types:
        chaos_types_dirs = chaos_data_dir + chaos_type
        chaos_names = os.listdir(chaos_types_dirs)
        kb_chaos_type_lst = []
        for chaos_name in chaos_names:
            chaos_path = chaos_types_dirs + "/" + chaos_name

            kb_unit = KB_Chaos(chaos_path)
            is_related, template = kb_unit.is_instance_related()
            template["instance_related"] = is_related

            for item in chaos_manage["Serial"][chaos_type]:
                if item["experiment"] == template["experiment"]:
                    index = item["index"]
                    template["index"] = index

            kb_chaos_type_lst.append(template)

        kb[chaos_type] = kb_chaos_type_lst

    return kb


def saveKB_to_file(kb, kb_path):
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    with open(kb_path, "w") as f:
        yaml.safe_dump(kb, f, default_flow_style=False, line_break=0)


def weighted_LCS(fingerprint, case, weight):

    WLCS = []

    def get_path(d, fingerprint, i, j):
        if i == 0 or j == 0:
            return []
        if d[i][j] == 0:
            get_path(d, fingerprint, i - 1, j - 1)
            WLCS.append(fingerprint[i - 1])
        elif d[i][j] == 1:
            return get_path(d, fingerprint, i - 1, j)
        else:
            return get_path(d, fingerprint, i, j - 1)

    path = [
        [0 for i in range(len(case) + 1)] for j in range(len(fingerprint) + 1)
    ]

    d = [[0 for i in range(len(case) + 1)] for j in range(len(fingerprint) + 1)]

    for idx_f, f in enumerate(fingerprint):
        for idx_c, c in enumerate(case):
            if f == c:
                path[idx_f + 1][idx_c + 1] = path[idx_f][idx_c] + weight[f]
                d[idx_f + 1][idx_c + 1] = 0
            elif path[idx_f][idx_c + 1] > path[idx_f + 1][idx_c]:
                path[idx_f + 1][idx_c + 1] = path[idx_f][idx_c + 1]
                d[idx_f + 1][idx_c + 1] = 1
            else:
                path[idx_f + 1][idx_c + 1] = path[idx_f + 1][idx_c]
                d[idx_f + 1][idx_c + 1] = -1

    get_path(d, fingerprint, len(fingerprint), len(case))

    return WLCS


if __name__ == "__main__":
    weight = {"a": 0.3, "b": 0.2, "c": 0.5, "d": 0.2, "e": 0.7}
    fingerprint = ["a", "b", "c", "e", "d", "e"]
    case = ["c", "d", "a", "e"]
    WLCS = weighted_LCS(fingerprint, case, weight)
    print(WLCS)
