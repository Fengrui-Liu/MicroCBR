import logging
import copy

_LOGGER = logging.getLogger(__name__)


class Weight:
    def __init__(self, item_list) -> None:
        self.item_list = item_list
        self.freq = {}
        self.degree = {}
        self.scores = {}
        self.co_occur = {}
        self.total_fingerprint = len(item_list)

    def __call__(self) -> dict:
        return self.cal_item_scores()

    def cal_item_scores(self):

        if self.freq or self.degree:
            _LOGGER.error("Please initialize the Rake before calculate scores!")
            return

        for item in self.item_list:
            item_len = len(item) - 1
            item_set = set(item)
            for unit in item_set:
                self.freq.setdefault(unit, 0)
                self.freq[unit] += 1

                self.degree.setdefault(unit, 0)
                self.degree[unit] += item_len

                self.co_occur.setdefault(unit, [])
                temp_item = copy.deepcopy(item_set)
                temp_item.remove(unit)
                self.co_occur[unit].extend(temp_item)

        for item in self.freq:
            self.degree[item] += self.freq[item]

        for item in self.freq:
            self.scores.setdefault(item, 0)

            rel = self.co_occur[item]
            w_rel = (
                1
                + (len(set(rel)) + 1) / (len(rel) + 1)
                + (len(set(rel)) + 1) / max(self.freq.values())
            )  # high with importance

            w_dif = self.freq[item] / self.total_fingerprint

            self.scores[item] = w_rel / ((w_dif / w_rel) + (len(rel) + 1))

        return self.scores


if __name__ == "__main__":
    item_list = [
        ["a", "b", "c"],
        ["a", "b", "c", "d", "e"],
        ["a", "b", "e"],
        ["f"],
    ]
    weight = Weight(item_list)
    scores = weight()
    print(weight.degree)
    print(weight.freq)
    print(weight.co_occur)
    print(scores)
