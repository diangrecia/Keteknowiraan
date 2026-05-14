import numpy as np

def calculate_user_color_preferences_004137e2-c10d-4543-8c00-b577ebfcb2de(image_hsv):
    user_preferences = [[0, 0, 0], [56, 100, 100], [348, 74, 73]]
    
    hue_img = image_hsv[:, :, 0].astype(np.int32)
    sat_img = image_hsv[:, :, 1]
    val_img = image_hsv[:, :, 2]
    
    hue_img = hue_img * 2
    
    unique_colors = set()
    height, width = image_hsv.shape[:2]
    
    for y in range(height):
        for x in range(width):
            h = hue_img[y, x]
            s = sat_img[y, x]
            v = val_img[y, x]
            unique_colors.add((h, s, v))
    
    extracted_colors = list(unique_colors)
    
    if len(extracted_colors) != len(user_preferences):
        return 0.0
    
    extracted_colors_sorted = sorted(extracted_colors)
    user_preferences_sorted = sorted(user_preferences)
    
    total_diff = 0.0
    for i in range(len(extracted_colors_sorted)):
        h_diff = abs(extracted_colors_sorted[i][0] - user_preferences_sorted[i][0])
        s_diff = abs(extracted_colors_sorted[i][1] - user_preferences_sorted[i][1])
        v_diff = abs(extracted_colors_sorted[i][2] - user_preferences_sorted[i][2])
        
        h_diff_normalized = h_diff / 360.0
        s_diff_normalized = s_diff / 255.0
        v_diff_normalized = v_diff / 255.0
        
        total_diff += h_diff_normalized + s_diff_normalized + v_diff_normalized
    
    max_possible_diff = 3 * len(extracted_colors_sorted)
    similarity = 1.0 - (total_diff / max_possible_diff)
    
    return max(0.0, similarity)