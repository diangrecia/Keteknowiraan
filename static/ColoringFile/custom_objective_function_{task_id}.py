import numpy as np

def calculate_user_color_preferences(image_hsv):
    user_preference = [[0, 0, 0], [359, 91, 55], [0, 0, 100]]
    
    hue_img = image_hsv[:, :, 0].astype(np.int32) * 2
    sat_img = image_hsv[:, :, 1].astype(np.int32)
    val_img = image_hsv[:, :, 2].astype(np.int32)
    
    unique_colors = set()
    for i in range(hue_img.shape[0]):
        for j in range(hue_img.shape[1]):
            h = hue_img[i, j] % 360
            s = sat_img[i, j]
            v = val_img[i, j]
            unique_colors.add((h, s, v))
    
    extracted_colors = sorted(list(unique_colors))
    
    if len(extracted_colors) != len(user_preference):
        return 0.0
    
    total_diff = 0
    for extracted, preferred in zip(extracted_colors, user_preference):
        h_diff = min(abs(extracted[0] - preferred[0]), 360 - abs(extracted[0] - preferred[0]))
        s_diff = abs(extracted[1] - preferred[1])
        v_diff = abs(extracted[2] - preferred[2])
        total_diff += h_diff + s_diff + v_diff
    
    max_possible_diff = len(user_preference) * (180 + 255 + 255)
    fitness = 1.0 - (total_diff / max_possible_diff)
    
    return max(0.0, fitness)