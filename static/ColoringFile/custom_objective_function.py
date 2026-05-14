import numpy as np

def calculate_user_color_preferences(image_hsv):
    user_prefs = np.array([[351, 90, 73], [335, 94, 69], [30, 20, 100]], dtype=np.int32)
    
    h, s, v = image_hsv[:, :, 0], image_hsv[:, :, 1], image_hsv[:, :, 2]
    hue_int = h.astype(np.int32) * 2
    unique_combinations = np.unique(np.column_stack((hue_int.ravel(), s.ravel(), v.ravel())), axis=0)
    
    if len(unique_combinations) != len(user_prefs):
        return 0.0
    
    sorted_user = np.sort(user_prefs.view('int32,int32,int32'), order=['f0', 'f1', 'f2']).view(np.int32).reshape(-1, 3)
    sorted_img = np.sort(unique_combinations.view('int32,int32,int32'), order=['f0', 'f1', 'f2']).view(np.int32).reshape(-1, 3)
    
    if np.array_equal(sorted_user, sorted_img):
        return 1.0
    
    hue_diff = np.abs(sorted_user[:, 0] - sorted_img[:, 0])
    hue_diff = np.minimum(hue_diff, 360 - hue_diff)
    sat_diff = np.abs(sorted_user[:, 1] - sorted_img[:, 1])
    val_diff = np.abs(sorted_user[:, 2] - sorted_img[:, 2])
    
    hue_penalty = np.mean(hue_diff / 180.0)
    sat_penalty = np.mean(sat_diff / 255.0)
    val_penalty = np.mean(val_diff / 255.0)
    
    fitness = 1.0 - (0.5 * hue_penalty + 0.3 * sat_penalty + 0.2 * val_penalty)
    return max(fitness, 0.0)