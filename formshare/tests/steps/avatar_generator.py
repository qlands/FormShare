def t_e_s_t_avatar_generator():
    from formshare.processes.avatar import Avatar

    Avatar.generate(45, "Carlos Quiros", "PNG")
    Avatar.generate(45, "CarlosQurios", "PNG")
    Avatar.generate(45, "CQC", "PNG")
    Avatar.generate(45, "CQ", "PNG")
    Avatar.generate(45, "C", "PNG")
    Avatar.generate(45, "", "PNG")
    Avatar.generate(45, "A B C", "PNG")
    Avatar.generate(45, "A B", "PNG")
