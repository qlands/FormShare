def t_e_s_t_color_hash_hex():
    from formshare.processes.color_hash import ColorHash

    color = ColorHash("FormShare")
    a = color.hex
    b = color.rgb
