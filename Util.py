class Util(object):

    @staticmethod
    def add3DimDict(dict, key_a, key_b, key_c, val):
        if key_a in dict.keys():
            if key_b in dict[key_a].keys():
                if key_c in dict[key_a][key_b].keys():
                    dict[key_a][key_b][key_c].update({key_b: val})
                else:
                    dict[key_a][key_b].update({key_c : val})
            else:
                dict[key_a].update({key_b : {key_c : val}})
        else:
            dict.update({key_a: {key_b: {key_c : val}}})
