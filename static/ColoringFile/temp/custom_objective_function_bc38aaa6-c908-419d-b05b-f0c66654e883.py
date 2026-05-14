import numpy as np

def calculate_user_color_preferences_bc38aaa6-c908-419d-b05b-f0c66654e883(image_hsv):
    user_preferences = [[0, 0, 0], [359, 91, 55], [0, 0, 100]]
    
    hue_img = image_hsv[:, :, 0].astype(np.int32)
    sat_img = image_hsv[:, :, 1].astype(np.int32)
    val_img = image_hsv[:, :, 2].astype(np.int32)
    
    hue_normalized = (hue_img * 2).astype(np.int32)
    unique_colors = set()
    
    for i in range(image_hsv.shape[0]):
        for j in range(image_hsv.shape[1]):
            h = hue_normalized[i, j]
            s = sat_img[i, j]
            v = val_img[i, j]
            unique_colors.add((h, s, v))
    
    extracted_colors = sorted(list(unique_colors))
    
    if len(extracted_colors) == len(user_preferences):
        match = True
        for extracted, preferred in zip(extracted_colors, user_preferences):
            if extracted[0] != preferred[0] or extracted[1] != preferred[1] or extracted[2] != preferred[2]:
                match = False
                break
        if match:
            return 1.0
    
    hue_diff = 0
    sat_diff = 0
    val_diff = 0
    
    for extracted in extracted_colors:
        min_hue_diff = float('inf')
        min_sat_diff = float('inf')
        min_val_diff = float('inf')
        
        for preferred in user_preferences:
            h_diff = min(abs(extracted[0] - preferred[0]), 360 - abs(extracted[0] - preferred[0]))
            s_diff = abs(extracted[1] - preferred[1])
            v_diff = abs(extracted[2] - preferred[2])
            
            min_hue_diff = min(min_hue_diff, h_diff)
            min_sat_diff = min(min_sat_diff, s_diff)
            min_val_diff = min(min_val_diff, v_diff)
        
        hue_diff += min_hue_diff
        sat_diff += min_sat_diff
        val_diff += min_val_diff
    
    total_diff = (hue_diff / 360.0 + sat_diff / 255.0 + val_diff / 255.0) / len(extracted_colors)
    fitness = max(0.0, 1.0 - total_diff)
    
    return fitness