def calculate_xp_gain(xp_gain: int, current_level: int, current_xp: int) -> tuple[int, int]:
    xp_to_level_up = current_level * 100
    total_xp = current_xp + xp_gain
    while total_xp >= xp_to_level_up:
        total_xp = total_xp - xp_to_level_up 
        current_level += 1 
        xp_to_level_up = current_level * 100 
    return current_level, total_xp

level = 1
current_xp = 50
xp_gain = 310
print(calculate_xp_gain(310, 1, 50))
print(calculate_xp_gain(10, 1, 50))
