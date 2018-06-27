import IPy


def _generate_switch_id_vmac(switch_id):
    assert (switch_id < 256 * 256)
    hex_str = str(hex(switch_id))
    xPos = hex_str.find('x')
    pure_hex_str = hex_str[xPos + 1:]
    pure_hex_str = '0' * (4 - len(pure_hex_str)) + pure_hex_str
    pure_hex_str = pure_hex_str[0:2] + ':' + pure_hex_str[2:]
    return pure_hex_str

if __name__=='__main__':
    a = 15
    print(_generate_switch_id_vmac(700))

